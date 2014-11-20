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

import os
import datetime
from common import *
import XenAPI
import time
import logging
import re
import os.path
import os
import datetime
import select
import urllib2
import base64
import socket
from stat import *


class copy_vm_xcp(backup_generic):
    """Backup a VM running on a XCP server on a second SR (requires xe tools and XenAPI)"""
    type = 'copy-vm-xcp'

    required_params = backup_generic.required_params + ['server_name','storage_name','password_file','vm_name','network_name']
    optional_params = backup_generic.optional_params + ['start_vm','max_copies']
    
    start_vm = "no"
    max_copies = 1
    
    
    def read_config(self,iniconf):
        assert(isinstance(iniconf,ConfigParser))
        backup_generic.read_config(self,iniconf)        
        if self.start_vm in 'no' and iniconf.has_option('global','start_vm'):
            self.start_vm = iniconf.get('global','start_vm')    
        if self.max_copies == 1 and iniconf.has_option('global','max_copies'):
            self.max_copies = iniconf.getint('global','max_copies')         
            
    
    def copy_vm_to_sr(self, vm_name, storage_name, dry_run):        
            user_xen, password_xen, null = open(self.password_file).read().split('\n')
            session = XenAPI.Session('https://'+self.server_name)
            try:
                session.login_with_password(user_xen,password_xen)
            except XenAPI.Failure, error:
                msg,ip = error.details
    
                if msg == 'HOST_IS_SLAVE':
                    server_name = ip
                    session = XenAPI.Session('https://'+server_name)
                    session.login_with_password(user_xen,password_xen)    
            
            
            self.logger.debug("[%s] VM (%s) to backup in storage: %s",self.backup_name,vm_name,storage_name)
            now = datetime.datetime.now()
            
            #get storage opaqueRef
            try:
                storage = session.xenapi.SR.get_by_name_label(storage_name)[0]
            except IndexError,error:
                result = (1,"error get SR opaqueref %s"%(error))
                return result
            
            
            #get vm to copy opaqueRef    
            try:
                vm = session.xenapi.VM.get_by_name_label(vm_name)[0]
            except IndexError,error:
                result = (1,"error get VM opaqueref %s"%(error))
                return result
            
            #do the snapshot    
            self.logger.debug("[%s] Snapshot in progress",self.backup_name)
            try:
                snapshot = session.xenapi.VM.snapshot(vm,"tisbackup-%s"%(vm_name))
            except XenAPI.Failure, error:
                result = (1,"error when snapshot %s"%(error))
                return result
            
            
            #get snapshot opaqueRef    
            snapshot = session.xenapi.VM.get_by_name_label("tisbackup-%s"%(vm_name))[0]
            session.xenapi.VM.set_name_description(snapshot,"snapshot created by tisbackup on : %s"%(now.strftime("%Y-%m-%d %H:%M")))
            
            
            
            vm_backup_name = "zzz-%s-"%(vm_name)
            
            
            #Check if old backup exit
            list_backups = []
            for vm_ref in session.xenapi.VM.get_all():
                name_lablel = session.xenapi.VM.get_name_label(vm_ref)
                if vm_backup_name in name_lablel:
                    list_backups.append(name_lablel)
                    
            list_backups.sort()
            
            if len(list_backups) >= 1:
                
                # Shutting last backup if started
                last_backup_vm = session.xenapi.VM.get_by_name_label(list_backups[-1])[0]
                if not "Halted" in session.xenapi.VM.get_power_state(last_backup_vm):
                    self.logger.debug("[%s] Shutting down last backup vm : %s", self.backup_name, list_backups[-1] )
                    session.xenapi.VM.hard_shutdown(last_backup_vm)
                
                # Delete oldest backup if exist
                if len(list_backups) >= int(self.max_copies):
                    for i in range(len(list_backups)-int(self.max_copies)+1):
                        oldest_backup_vm = session.xenapi.VM.get_by_name_label(list_backups[i])[0]
                        if not "Halted" in session.xenapi.VM.get_power_state(oldest_backup_vm):
                            self.logger.debug("[%s] Shutting down old vm : %s", self.backup_name, list_backups[i] )                    
                            session.xenapi.VM.hard_shutdown(oldest_backup_vm)
                            
                        try:
                            self.logger.debug("[%s] Deleting old vm : %s", self.backup_name, list_backups[i])
                            for vbd in session.xenapi.VM.get_VBDs(oldest_backup_vm):
                                if session.xenapi.VBD.get_type(vbd) == 'CD'and session.xenapi.VBD.get_record(vbd)['empty'] == False:
                                    session.xenapi.VBD.eject(vbd)                                   
                                else:
                                    vdi = session.xenapi.VBD.get_VDI(vbd)
                                    if not 'NULL' in  vdi:
                                        session.xenapi.VDI.destroy(vdi)
                                
                            session.xenapi.VM.destroy(oldest_backup_vm)                
                        except XenAPI.Failure, error:
                            result = (1,"error when destroy old backup vm %s"%(error))
                            return result
                    
                    
            self.logger.debug("[%s] Copy %s in progress on %s",self.backup_name,vm_name,storage_name)
            try:
                backup_vm = session.xenapi.VM.copy(snapshot,vm_backup_name+now.strftime("%Y-%m-%d %H:%M"),storage)
            except XenAPI.Failure, error:
                result = (1,"error when copy %s"%(error))
                return result
            
            
            # define VM as a template
            session.xenapi.VM.set_is_a_template(backup_vm,False)
            
            #change the network of the new VM
            try:
                vifDestroy = session.xenapi.VM.get_VIFs(backup_vm)
            except IndexError,error:
                result = (1,"error get VIF opaqueref %s"%(error))
                return result
            
            
            for i in vifDestroy:
                vifRecord = session.xenapi.VIF.get_record(i)
                session.xenapi.VIF.destroy(i)
                networkRef = session.xenapi.network.get_by_name_label(self.network_name)[0]
                data = {'MAC': vifRecord['MAC'],
                        'MAC_autogenerated': False,
                        'MTU': vifRecord['MTU'],
                        'VM': backup_vm,
                        'current_operations': vifRecord['current_operations'],
                        'currently_attached': vifRecord['currently_attached'],
                        'device': vifRecord['device'],
                        'ipv4_allowed': vifRecord['ipv4_allowed'],
                        'ipv6_allowed': vifRecord['ipv6_allowed'],
                        'locking_mode': vifRecord['locking_mode'],
                        'network': networkRef,
                        'other_config': vifRecord['other_config'],
                        'qos_algorithm_params': vifRecord['qos_algorithm_params'],
                        'qos_algorithm_type': vifRecord['qos_algorithm_type'],
                        'qos_supported_algorithms': vifRecord['qos_supported_algorithms'],
                        'runtime_properties': vifRecord['runtime_properties'],
                        'status_code': vifRecord['status_code'],
                        'status_detail': vifRecord['status_detail']
                        }
                try:
                    session.xenapi.VIF.create(data)
                except Exception, error:
                    result = (1,error)
                    return result
            
            
            if self.start_vm in ['true', '1', 't', 'y', 'yes', 'oui']:
                session.xenapi.VM.start(backup_vm,False,True)
            
            session.xenapi.VM.set_name_description(backup_vm,"snapshot created by tisbackup on : %s"%(now.strftime("%Y-%m-%d %H:%M")))
            
            size_backup = 0
            for vbd in session.xenapi.VM.get_VBDs(backup_vm):
                if session.xenapi.VBD.get_type(vbd) == 'CD' and session.xenapi.VBD.get_record(vbd)['empty'] == False:
                    session.xenapi.VBD.eject(vbd)
                else:
                    vdi = session.xenapi.VBD.get_VDI(vbd)
                    if not 'NULL' in  vdi:
                        size_backup = size_backup + int(session.xenapi.VDI.get_record(vdi)['physical_utilisation'])
                
            #delete the snapshot
            try:
                for vbd in session.xenapi.VM.get_VBDs(snapshot):
                    if session.xenapi.VBD.get_type(vbd) == 'CD' and session.xenapi.VBD.get_record(vbd)['empty'] == False:
                        session.xenapi.VBD.eject(vbd)
                    else:
                        vdi = session.xenapi.VBD.get_VDI(vbd)
                        if not 'NULL' in  vdi:
                            session.xenapi.VDI.destroy(vdi)
                session.xenapi.VM.destroy(snapshot)
            except XenAPI.Failure, error:
                result = (1,"error when destroy snapshot %s"%(error))
                return result
            
            result = (0,size_backup)
            return result
        
        
    def do_backup(self,stats):
        try:
            timestamp = int(time.time())
            cmd = self.copy_vm_to_sr(self.vm_name, self.storage_name, self.dry_run)
            
            if cmd[0] == 0:
                timeExec = int(time.time()) - timestamp
                stats['log']='copy of %s to an other storage OK' % (self.backup_name)
                stats['status']='OK'
                stats['total_files_count'] = 1
                stats['total_bytes'] = cmd[1]
                
                stats['backup_location'] = self.storage_name
            else:
                stats['status']='ERROR'
                stats['log']=cmd[1]

        except BaseException,e:
            stats['status']='ERROR'
            stats['log']=str(e)
            raise

register_driver(copy_vm_xcp)            