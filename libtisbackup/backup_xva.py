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


class backup_xva(backup_generic):
    """Backup a VM running on a XCP server as a XVA file (requires xe tools and XenAPI)"""
    type = 'xen-xva'
    
    required_params = backup_generic.required_params + ['xcphost','password_file','server_name']
    optional_params = backup_generic.optional_params + ['excluded_vbds','remote_user','private_key']
    
    def export_xva(self, vdi_name, filename, dry_run):

        user_xen, password_xen, null = open(self.password_file).read().split('\n')
        session = XenAPI.Session('https://'+self.xcphost)
        try:
            session.login_with_password(user_xen,password_xen)
        except XenAPI.Failure, error:
            msg,ip = error.details
        
            if msg == 'HOST_IS_SLAVE':
                xcphost = ip
                session = XenAPI.Session('https://'+xcphost)
                session.login_with_password(user_xen,password_xen)
        
        vm = session.xenapi.VM.get_by_name_label(vdi_name)[0]
        status_vm = session.xenapi.VM.get_power_state(vm)
        
        self.logger.debug("[%s] Status of VM: %s",self.backup_name,status_vm)
        if status_vm == "Running":
            self.logger.debug("[%s] Shudown in progress",self.backup_name)
            if dry_run:
                print "session.xenapi.VM.clean_shutdown(vm)"
                
            else:
                session.xenapi.VM.clean_shutdown(vm)
        
        try:
            try:
                self.logger.debug("[%s] Copy in progress",self.backup_name)
                
                socket.setdefaulttimeout(120)
                auth = base64.encodestring("%s:%s" % (user_xen, password_xen)).strip()
                url = "https://"+self.xcphost+"/export?uuid="+session.xenapi.VM.get_uuid(vm)
                request = urllib2.Request(url)
                request.add_header("Authorization", "Basic %s" % auth)
                result = urllib2.urlopen(request)
                
                if dry_run:
                    print "request = urllib2.Request(%s)" % url
                    print 'outputfile = open(%s, "wb")' % filename
                else:
                    outputfile = open(filename, "wb")
                    for line in result:
                        outputfile.write(line)
                    outputfile.close()

            except:
                if os.path.exists(filename):
                    os.unlink(filename)
                raise 
        
        finally:
            if status_vm == "Running":
                self.logger.debug("[%s] Starting in progress",self.backup_name)
                if dry_run:
                    print "session.xenapi.Async.VM.start(vm,False,True)"
                else:
                    session.xenapi.Async.VM.start(vm,False,True)
        
            session.logout()
        
        if os.path.exists(filename):
            import tarfile
            tar = tarfile.open(filename)
            if not tar.getnames():
                unlink(filename)
                return("Tar error")
            tar.close()

        return(0)

        
    

    def do_backup(self,stats):
        try:
            dest_filename = os.path.join(self.backup_dir,"%s-%s.%s" % (self.backup_name,self.backup_start_date,'xva'))
            
            options = []               
            options_params = " ".join(options)
            cmd = self.export_xva( self.server_name, dest_filename, self.dry_run)
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
                stats['status']='ERROR'
                stats['log']=cmd



        except BaseException , e:
            stats['status']='ERROR'
            stats['log']=str(e)
            raise



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

