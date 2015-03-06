#!/usr/bin/python
# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------
#    This file is part of TISBackup
#
#    TISBackup is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    TISBackup is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with TISBackup.  If not, see <http://www.gnu.org/licenses/>.
#
# -----------------------------------------------------------------------
from __future__ import with_statement
from common import *
import pyVmomi
from pyVmomi import vim
from pyVmomi import vmodl
from pyVim.connect import SmartConnect, Disconnect

from datetime import datetime, date, timedelta
import atexit
import getpass
import requests
# Disable HTTPS verification warnings.
from requests.packages import urllib3
urllib3.disable_warnings()
import os
import time
import tarfile
import re 
import xml.etree.ElementTree as ET

from stat import *


class backup_vmdk(backup_generic):
    type = 'esx-vmdk'

    required_params = backup_generic.required_params + ['esxhost','password_file','server_name']
    optional_params = backup_generic.optional_params + ['esx_port', 'prefix_clone', 'create_ovafile']

    esx_port = 443
    prefix_clone = "clone-"
    create_ovafile = "no"

    def make_compatible_cookie(self,client_cookie):
        cookie_name = client_cookie.split("=", 1)[0]
        cookie_value = client_cookie.split("=", 1)[1].split(";", 1)[0]
        cookie_path = client_cookie.split("=", 1)[1].split(";", 1)[1].split(
            ";", 1)[0].lstrip()
        cookie_text = " " + cookie_value + "; $" + cookie_path
        # Make a cookie
        cookie = dict()
        cookie[cookie_name] = cookie_text   
        return cookie


    def download_file(self,url, local_filename, cookie, headers):
        r = requests.get(url, stream=True, headers=headers,cookies=cookie,verify=False)
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024*64): 
                if chunk: 
                    f.write(chunk)
                    f.flush()
        return local_filename


    def export_vmdks(self,vm):
        HttpNfcLease = vm.ExportVm()
        try:
            infos = HttpNfcLease.info
            device_urls = infos.deviceUrl
            vmdks = []        
            for device_url in device_urls:
                deviceId = device_url.key
                deviceUrlStr = device_url.url
                diskFileName =  vm.name.replace(self.prefix_clone,'') + "-" + device_url.targetId
                diskUrlStr = deviceUrlStr.replace("*", self.esxhost)
                diskLocalPath = './' + diskFileName

                cookie = self.make_compatible_cookie(si._stub.cookie)
                headers = {'Content-Type': 'application/octet-stream'}
                self.logger.debug("[%s] exporting disk: %s" %(self.server_name,diskFileName))
                
                self.download_file(diskUrlStr, diskFileName, cookie, headers)
                vmdks.append({"filename":diskFileName,"id":deviceId})
        finally:
            HttpNfcLease.Complete()
        return vmdks


    def create_ovf(self,vm,vmdks):
        ovfDescParams = vim.OvfManager.CreateDescriptorParams()
        ovf = si.content.ovfManager.CreateDescriptor(vm, ovfDescParams)     
        root = ET.fromstring(ovf.ovfDescriptor)  
        new_id = root[0][1].attrib.values()[0][1:3]
        ovfFiles = []
        for vmdk in vmdks:
            old_id =  vmdk['id'][1:3]
            id = vmdk['id'].replace(old_id,new_id)
            ovfFiles.append(vim.OvfManager.OvfFile(size=os.path.getsize(vmdk['filename']), path=vmdk['filename'], deviceId=id))

        ovfDescParams = vim.OvfManager.CreateDescriptorParams()
        ovfDescParams.ovfFiles = ovfFiles;                

        ovf = si.content.ovfManager.CreateDescriptor(vm, ovfDescParams)     
        ovf_filename = vm.name+".ovf"
        self.logger.debug("[%s] creating ovf file: %s" %(self.server_name,ovf_filename))
        
        with open(ovf_filename, "w") as f: 
            f.write(ovf.ovfDescriptor)     
        return ovf_filename

    def create_ova(self,vm, vmdks, ovf_filename):
        ova_filename = vm.name+".ova"
        vmdks.insert(0,{"filename":ovf_filename,"id":"false"})
        self.logger.debug("[%s] creating ova file: %s" %(self.server_name,ova_filename))
        with tarfile.open(ova_filename, "w")  as tar:
            for vmdk in vmdks:
                tar.add(vmdk['filename'])
                os.unlink(vmdk['filename'])
        return ova_filename

    def clone_vm(self,vm):
        task = self.wait_task(vm.CreateSnapshot_Task(name="backup",description="Automatic backup "+datetime.now().strftime("%Y-%m-%d %H:%M:%s"),memory=False,quiesce=True))
        snapshot=task.info.result 
        prefix_vmclone = self.prefix_clone
        clone_name = prefix_vmclone + vm.name 
        datastore = '[%s]' % vm.datastore[0].name



        vmx_file = vim.vm.FileInfo(logDirectory=None,
                                   snapshotDirectory=None,
                                   suspendDirectory=None,
                                   vmPathName=datastore)

        config = vim.vm.ConfigSpec(name=clone_name, memoryMB=vm.summary.config.memorySizeMB, numCPUs=vm.summary.config.numCpu, files=vmx_file)

        hosts = datacenter.hostFolder.childEntity
        resource_pool = hosts[0].resourcePool    

        self.wait_task(vmFolder.CreateVM_Task(config=config,pool=resource_pool))   

        new_vm = [x for x in vmFolder.childEntity if x.name == clone_name][0]

        controller  = vim.vm.device.VirtualDeviceSpec()
        controller.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        controller.device = vim.vm.device.VirtualLsiLogicController(busNumber=0,sharedBus='noSharing')       
        controller.device.key = 0    
        i=0

        vm_devices = []
        clone_folder = "%s/" % "/".join(new_vm.summary.config.vmPathName.split('/')[:-1])
        for device in vm.config.hardware.device:
            if device.__class__.__name__ == 'vim.vm.device.VirtualDisk':
                cur_vers = int(re.findall(r'\d{3,6}', device.backing.fileName)[0])

                if cur_vers == 1:
                    source = device.backing.fileName.replace('-000001','')
                else:
                    source = device.backing.fileName.replace('%d.' % cur_vers,'%d.' % ( cur_vers - 1 ))


                dest = clone_folder+source.split('/')[-1]
                disk_spec = vim.VirtualDiskManager.VirtualDiskSpec(diskType="sparseMonolithic",adapterType="ide")
                self.wait_task(si.content.virtualDiskManager.CopyVirtualDisk_Task(sourceName=source,destName=dest,destSpec=disk_spec))
               # self.wait_task(si.content.virtualDiskManager.ShrinkVirtualDisk_Task(dest))

                diskfileBacking = vim.vm.device.VirtualDisk.FlatVer2BackingInfo()
                diskfileBacking.fileName = dest
                diskfileBacking.diskMode =  "persistent"
                vdisk_spec = vim.vm.device.VirtualDeviceSpec()
                vdisk_spec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
                vdisk_spec.device = vim.vm.device.VirtualDisk(capacityInKB=10000 ,controllerKey=controller.device.key)
                vdisk_spec.device.key = 0
                vdisk_spec.device.backing = diskfileBacking
                vdisk_spec.device.unitNumber = i
                vm_devices.append(vdisk_spec)
                i+=1



        vm_devices.append(controller)    

        config.deviceChange=vm_devices
        self.wait_task(new_vm.ReconfigVM_Task(config))
        self.wait_task(snapshot.RemoveSnapshot_Task(removeChildren=True))
        return new_vm
    def wait_task(self,task):
        while task.info.state in ["queued", "running"]:
            time.sleep(2)
        self.logger.debug("[%s] %s",self.server_name,task.info.descriptionId)       
        return task




    def do_backup(self,stats):
        try:
            dest_dir = os.path.join(self.backup_dir,"%s" % self.backup_start_date)
            if not os.path.isdir(dest_dir):
                if not self.dry_run:
                    os.makedirs(dest_dir)
                else:
                    print 'mkdir "%s"' % dest_dir
            else:
                raise Exception('backup destination directory already exists : %s' % dest_dir)            
            os.chdir(dest_dir)
            user_esx, password_esx, null = open(self.password_file).read().split('\n')

            global si
            si = SmartConnect(host=self.esxhost,user=user_esx,pwd=password_esx,port=self.esx_port)

            if not si:
                raise Exception("Could not connect to the specified host using specified "
                      "username and password")

            atexit.register(Disconnect, si)

            content = si.RetrieveContent()
            for child in content.rootFolder.childEntity:
                if hasattr(child, 'vmFolder'):
                    global vmFolder, datacenter
                    datacenter = child
                    vmFolder = datacenter.vmFolder
                    vmList = vmFolder.childEntity
                    for vm in vmList:
                        if vm.name == self.server_name:
                            if not vm.summary.runtime.powerState == "poweredOff":
                                new_vm = self.clone_vm(vm)
                                vmdks = self.export_vmdks(new_vm)
                                ovf_filename = self.create_ovf(vm, vmdks)
                                if str2bool(self.create_ovafile):
                                    ova_filename = self.create_ova(vm, vmdks, ovf_filename)    
                                self.wait_task(new_vm.Destroy_Task())
                            else:
                                vmdks = self.export_vmdks(vm)
                                ovf_filename = self.create_ovf(vm, vmdks)
                                if str2bool(self.create_ovafile):
                                    ova_filename = self.create_ova(vm, vmdks, ovf_filename)                                   


            if os.path.exists(dest_dir):
                for file in os.listdir(dest_dir):                    
                    stats['written_bytes'] += os.stat(file)[ST_SIZE]
                    stats['total_files_count'] += 1
                    stats['written_files_count'] += 1
                stats['total_bytes'] =  stats['written_bytes']
            else:
                stats['written_bytes'] = 0

            stats['backup_location'] = dest_dir
            
            stats['log']='XVA backup from %s OK, %d bytes written' % (self.server_name,stats['written_bytes'])
            stats['status']='OK'    
            

        except BaseException , e:
            stats['status']='ERROR'
            stats['log']=str(e)
            raise



register_driver(backup_vmdk)

