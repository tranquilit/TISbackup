#!/usr/bin/python3
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

import logging
import re
import os
import datetime
import urllib.request, urllib.parse, urllib.error
import socket
import tarfile
import hashlib
from stat import *
import ssl
import requests

from .common import *
from . import XenAPI

if hasattr(ssl, '_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context


class backup_xva(backup_generic):
    """Backup a VM running on a XCP server as a XVA file (requires xe tools and XenAPI)"""
    type = 'xen-xva'

    required_params = backup_generic.required_params + ['xcphost','password_file','server_name']
    optional_params = backup_generic.optional_params + ['enable_https', 'halt_vm', 'verify_export', 'reuse_snapshot', 'ignore_proxies', 'use_compression' ]

    enable_https = "no"
    halt_vm = "no"
    verify_export = "no"
    reuse_snapshot = "no"
    ignore_proxies = "yes"
    use_compression = "true"

    if str2bool(ignore_proxies):
        os.environ['http_proxy']=""
        os.environ['https_proxy']=""

    def verify_export_xva(self,filename):
        self.logger.debug("[%s] Verify xva export integrity",self.server_name)
        tar = tarfile.open(filename)
        members = tar.getmembers()
        for tarinfo in members:
            if re.search(r'^[0-9]*$',os.path.basename(tarinfo.name)):
                sha1sum = hashlib.sha1(tar.extractfile(tarinfo).read()).hexdigest()
                sha1sum2 = tar.extractfile(tarinfo.name+'.checksum').read()
                if not sha1sum == sha1sum2:
                    raise Exception("File corrupt")
        tar.close()

    def export_xva(self, vdi_name, filename, halt_vm,dry_run,enable_https=True, reuse_snapshot="no"):

        user_xen, password_xen, null = open(self.password_file).read().split('\n')
        session = XenAPI.Session('https://'+self.xcphost)
        try:
            session.login_with_password(user_xen,password_xen)
        except XenAPI.Failure as error:
            msg,ip = error.details

            if msg == 'HOST_IS_SLAVE':
                xcphost = ip
                session = XenAPI.Session('https://'+xcphost)
                session.login_with_password(user_xen,password_xen)

        if not session.xenapi.VM.get_by_name_label(vdi_name):
            return "bad VM name: %s" % vdi_name

        vm = session.xenapi.VM.get_by_name_label(vdi_name)[0]
        status_vm = session.xenapi.VM.get_power_state(vm)

        self.logger.debug("[%s] Check if previous fail backups exist",vdi_name)
        backups_fail  =  files = [f for f in os.listdir(self.backup_dir) if f.startswith(vdi_name) and f.endswith(".tmp")]
        for backup_fail in backups_fail:
            self.logger.debug('[%s] Delete backup "%s"', vdi_name, backup_fail)
            os.unlink(os.path.join(self.backup_dir, backup_fail))



        #add snapshot option
        if not str2bool(halt_vm):
            self.logger.debug("[%s] Check if previous tisbackups snapshots exist",vdi_name)
            old_snapshots =  session.xenapi.VM.get_by_name_label("tisbackup-%s"%(vdi_name))
            self.logger.debug("[%s] Old snaps count %s", vdi_name, len(old_snapshots))

            if len(old_snapshots) == 1 and str2bool(reuse_snapshot) == True:
                snapshot = old_snapshots[0]
                self.logger.debug("[%s] Reusing snap \"%s\"", vdi_name, session.xenapi.VM.get_name_description(snapshot))
                vm = snapshot # vm = session.xenapi.VM.get_by_name_label("tisbackup-%s"%(vdi_name))[0]
            else:
                self.logger.debug("[%s] Deleting %s old snaps", vdi_name, len(old_snapshots))
                for old_snapshot in old_snapshots:
                    self.logger.debug("[%s] Destroy snapshot %s",vdi_name,session.xenapi.VM.get_name_description(old_snapshot))
                    try:
                        for vbd in session.xenapi.VM.get_VBDs(old_snapshot):
                            if session.xenapi.VBD.get_type(vbd) == 'CD' and session.xenapi.VBD.get_record(vbd)['empty'] == False:
                                session.xenapi.VBD.eject(vbd)
                            else:
                                vdi = session.xenapi.VBD.get_VDI(vbd)
                                if not 'NULL' in  vdi:
                                    session.xenapi.VDI.destroy(vdi)
                        session.xenapi.VM.destroy(old_snapshot)
                    except XenAPI.Failure as error:
                        return("error when destroy snapshot %s"%(error))

                now = datetime.datetime.now()
                self.logger.debug("[%s] Snapshot in progress",vdi_name)
                try:
                    snapshot = session.xenapi.VM.snapshot(vm,"tisbackup-%s"%(vdi_name))
                    self.logger.debug("[%s] got snapshot %s", vdi_name, snapshot)
                except XenAPI.Failure as error:
                    return("error when snapshot %s"%(error))
                #get snapshot opaqueRef
                vm = session.xenapi.VM.get_by_name_label("tisbackup-%s"%(vdi_name))[0]
                session.xenapi.VM.set_name_description(snapshot,"snapshot created by tisbackup on: %s"%(now.strftime("%Y-%m-%d %H:%M")))
        else:
            self.logger.debug("[%s] Status of VM: %s",self.backup_name,status_vm)
            if status_vm == "Running":
                self.logger.debug("[%s] Shudown in progress",self.backup_name)
                if dry_run:
                    print("session.xenapi.VM.clean_shutdown(vm)")
                else:
                    session.xenapi.VM.clean_shutdown(vm)
        try:
            try:
                filename_temp = filename+".tmp"
                self.logger.debug("[%s] Copy in progress",self.backup_name)
                if not str2bool(self.use_compression):
                    socket.setdefaulttimeout(120)

                scheme = "http://"
                if str2bool(enable_https):
                    scheme = "https://"
                url = scheme+user_xen+":"+password_xen+"@"+self.xcphost+"/export?use_compression="+self.use_compression+"&uuid="+session.xenapi.VM.get_uuid(vm)




                top_level_url = scheme+self.xcphost+"/export?use_compression="+self.use_compression+"&uuid="+session.xenapi.VM.get_uuid(vm)
                r = requests.get(top_level_url, auth=(user_xen, password_xen))
                open(filename_temp, 'wb').write(r.content)


            except Exception as e:
                self.logger.error("[%s] error when fetching snap: %s", "tisbackup-%s"%(vdi_name), e)
                if os.path.exists(filename_temp):
                    os.unlink(filename_temp)
                raise

        finally:
            if not str2bool(halt_vm):
                self.logger.debug("[%s] Destroy snapshot",'tisbackup-%s'%(vdi_name))
                try:
                    for vbd in session.xenapi.VM.get_VBDs(snapshot):
                        if session.xenapi.VBD.get_type(vbd) == 'CD' and session.xenapi.VBD.get_record(vbd)['empty'] == False:
                            session.xenapi.VBD.eject(vbd)
                        else:
                            vdi = session.xenapi.VBD.get_VDI(vbd)
                            if not 'NULL' in  vdi:
                                session.xenapi.VDI.destroy(vdi)
                    session.xenapi.VM.destroy(snapshot)
                except XenAPI.Failure as error:
                    return("error when destroy snapshot %s"%(error))

            elif status_vm == "Running":
                self.logger.debug("[%s] Starting in progress",self.backup_name)
                if dry_run:
                    print("session.xenapi.Async.VM.start(vm,False,True)")
                else:
                    session.xenapi.Async.VM.start(vm,False,True)

            session.logout()

        if os.path.exists(filename_temp):
            tar = os.system('tar tf "%s" > /dev/null' % filename_temp)
            if not tar == 0:
                os.unlink(filename_temp)
                return("Tar error")
            if str2bool(self.verify_export):
                self.verify_export_xva(filename_temp)
            os.rename(filename_temp,filename)

        return(0)




    def do_backup(self,stats):
        try:
            dest_filename = os.path.join(self.backup_dir,"%s-%s.%s" % (self.backup_name,self.backup_start_date,'xva'))

            options = []
            options_params = " ".join(options)
            cmd = self.export_xva( vdi_name= self.server_name,filename= dest_filename, halt_vm= self.halt_vm, enable_https=self.enable_https, dry_run= self.dry_run, reuse_snapshot=self.reuse_snapshot)
            if os.path.exists(dest_filename):
                stats['written_bytes'] = os.stat(dest_filename)[ST_SIZE]
                stats['total_files_count'] = 1
                stats['written_files_count'] = 1
                stats['total_bytes'] =  stats['written_bytes']
            else:
                stats['written_bytes'] = 0

            stats['backup_location'] = dest_filename
            if cmd == 0:
                stats['log']='XVA backup from %s OK, %d bytes written' % (self.server_name,stats['written_bytes'])
                stats['status']='OK'
            else:
                raise Exception(cmd)

        except BaseException as e:
            stats['status']='ERROR'
            stats['log']=str(e)
            raise


    def register_existingbackups(self):
        """scan backup dir and insert stats in database"""

        registered = [b['backup_location'] for b in self.dbstat.query('select distinct backup_location from stats where backup_name=?',(self.backup_name,))]

        filelist = os.listdir(self.backup_dir)
        filelist.sort()
        for item in filelist:
            if item.endswith('.xva'):
                dir_name = os.path.join(self.backup_dir,item)
                if not dir_name in registered:
                    start = (datetime.datetime.strptime(item,self.backup_name+'-%Y%m%d-%Hh%Mm%S.xva') + datetime.timedelta(0,30*60)).isoformat()
                    if fileisodate(dir_name)>start:
                        stop = fileisodate(dir_name)
                    else:
                        stop = start
                    self.logger.info('Registering %s started on %s',dir_name,start)
                    self.logger.debug('  Disk usage %s','du -sb "%s"' % dir_name)
                    if not self.dry_run:
                        size_bytes = int(os.popen('du -sb "%s"' % dir_name).read().split('\t')[0])
                    else:
                        size_bytes = 0
                    self.logger.debug('  Size in bytes : %i',size_bytes)
                    if not self.dry_run:
                        self.dbstat.add(self.backup_name,self.server_name,'',\
                                        backup_start=start,backup_end = stop,status='OK',total_bytes=size_bytes,backup_location=dir_name,TYPE='BACKUP')
                else:
                    self.logger.info('Skipping %s, already registered',dir_name)


register_driver(backup_xva)

if __name__=='__main__':
    logger = logging.getLogger('tisbackup')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    cp = ConfigParser()
    cp.read('/opt/tisbackup/configtest.ini')
    b = backup_xva()
    b.read_config(cp)
