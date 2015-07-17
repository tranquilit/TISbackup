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
import sys
try:
    sys.stderr = open('/dev/null')       # Silence silly warnings from paramiko
    import paramiko
except ImportError,e:
    print "Error : can not load paramiko library %s" % e
    raise

sys.stderr = sys.__stderr__

import datetime
import base64
import os
from common import *
import re

class backup_oracle(backup_generic):
    """Backup a oracle database as zipped file through ssh"""
    type = 'oracle+ssh'    
    required_params = backup_generic.required_params + ['db_name','private_key', 'userid']
    optional_params = ['username', 'remote_backup_dir', 'ignore_error_oracle_code']
    db_name=''
    username='oracle'
    remote_backup_dir =  r'/home/oracle/backup'
    ignore_error_oracle_code = [ ]

    def do_backup(self,stats):
        
        self.logger.debug('[%s] Connecting to %s with user %s and key %s',self.backup_name,self.server_name,self.username,self.private_key)
        try:
            mykey = paramiko.RSAKey.from_private_key_file(self.private_key)
        except paramiko.SSHException:
            mykey = paramiko.DSSKey.from_private_key_file(self.private_key)

        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.server_name,username=self.username,pkey = mykey,port=self.ssh_port)      
        
        t = datetime.datetime.now()
        self.backup_start_date =  t.strftime('%Y%m%d-%Hh%Mm%S')
        dumpfile= self.remote_backup_dir + '/' + self.db_name + '_' + self.backup_start_date+'.dmp'
        dumplog = self.remote_backup_dir + '/' + self.db_name + '_' + self.backup_start_date+'.log'

        self.dest_dir = os.path.join(self.backup_dir,self.backup_start_date)
        
        # dump db
        stats['status']='Dumping'
        cmd = "exp '%s'  file='%s' grants=y log='%s'"% (self.userid,dumpfile, dumplog) 
        self.logger.debug('[%s] Dump DB : %s',self.backup_name,cmd)
        if not self.dry_run:
            (error_code,output) = ssh_exec(cmd,ssh=self.ssh)
            self.logger.debug("[%s] Output of %s :\n%s",self.backup_name,cmd,output)
            if error_code:
                localpath = os.path.join(self.dest_dir , self.db_name + '.log')
                self.logger.debug('[%s] Get log file with sftp on %s from %s to %s',self.backup_name,self.server_name,dumplog,localpath)
                transport =  self.ssh.get_transport()
                sftp = paramiko.SFTPClient.from_transport(transport)
                sftp.get(dumplog, localpath)
                sftp.close()

                file = open(localpath)
                for line in file:
                    if re.search('EXP-[0-9]+:', line) and not re.match('EXP-[0-9]+:', line).group(0).replace(':','') in self.ignore_error_oracle_code:
                        stats['status']='RMTemp'
                        self.clean_dumpfiles(dumpfile,dumplog)
                        raise Exception('Aborting, Not null exit code (%s) for "%s"' % (re.match('EXP-[0-9]+:', line).group(0).replace(':',''),cmd))
                file.close()

        # zip the file
        stats['status']='Zipping'
        cmd = 'gzip  %s' % dumpfile 
        self.logger.debug('[%s] Compress backup : %s',self.backup_name,cmd)
        if not self.dry_run:
            (error_code,output) = ssh_exec(cmd,ssh=self.ssh)
            self.logger.debug("[%s] Output of %s :\n%s",self.backup_name,cmd,output)
        if error_code:
            raise Exception('Aborting, Not null exit code (%i) for "%s"' % (error_code,cmd))

        # get the file
        stats['status']='SFTP'
        filepath = dumpfile + '.gz'
        localpath = os.path.join(self.dest_dir , self.db_name + '.dmp.gz')
        self.logger.debug('[%s] Get gz backup with sftp on %s from %s to %s',self.backup_name,self.server_name,filepath,localpath)
        if not self.dry_run:
            transport =  self.ssh.get_transport()
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.get(filepath, localpath)
            sftp.close()

        if not self.dry_run:
            stats['total_files_count']=1
            stats['written_files_count']=1
            stats['total_bytes']=os.stat(localpath).st_size
            stats['written_bytes']=os.stat(localpath).st_size    
        stats['log']='gzip dump of DB %s:%s (%d bytes) to %s' % (self.server_name,self.db_name, stats['written_bytes'], localpath)
        stats['backup_location'] = self.dest_dir
        stats['status']='RMTemp'
        self.clean_dumpfiles(dumpfile,dumplog)
        stats['status']='OK'

    def register_existingbackups(self):
        """scan backup dir and insert stats in database"""

        registered = [b['backup_location'] for b in self.dbstat.query('select distinct backup_location from stats where backup_name=?',(self.backup_name,))]

        filelist = os.listdir(self.backup_dir)
        filelist.sort()
        p = re.compile('^\d{8,8}-\d{2,2}h\d{2,2}m\d{2,2}$') 
        for item in filelist:
            if p.match(item):
                dir_name = os.path.join(self.backup_dir,item)
                if not dir_name in registered:
                    start = datetime.datetime.strptime(item,'%Y%m%d-%Hh%Mm%S').isoformat()
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
                                        backup_start=start,backup_end = stop,status='OK',total_bytes=size_bytes,backup_location=dir_name)
                else:
                    self.logger.info('Skipping %s, already registered',dir_name)


    def clean_dumpfiles(self,dumpfile,dumplog):
        cmd = 'rm -f "%s.gz" "%s"' %( dumpfile , dumplog)
        self.logger.debug('[%s] Remove temp gzip : %s',self.backup_name,cmd)
        if not self.dry_run:
            (error_code,output) = ssh_exec(cmd,ssh=self.ssh)
            self.logger.debug("[%s] Output of %s :\n%s",self.backup_name,cmd,output)
            if error_code:
                raise Exception('Aborting, Not null exit code (%i) for "%s"' % (error_code,cmd))
        cmd = 'rm -f '+self.remote_backup_dir  + '/' + self.db_name + '_' + self.backup_start_date+'.dmp'
        self.logger.debug('[%s] Remove temp dump : %s',self.backup_name,cmd)
        if not self.dry_run:
            (error_code,output) = ssh_exec(cmd,ssh=self.ssh)
            self.logger.debug("[%s] Output of %s :\n%s",self.backup_name,cmd,output)
            if error_code:
                raise Exception('Aborting, Not null exit code (%i) for "%s"' % (error_code,cmd))

register_driver(backup_oracle)