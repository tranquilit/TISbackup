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

class backup_sqlserver(backup_generic):
    """Backup a SQLSERVER database as gzipped sql file through ssh"""
    type = 'sqlserver+ssh'    
    required_params = backup_generic.required_params + ['db_name','private_key']
    optional_params = ['username', 'remote_backup_dir', 'sqlserver_before_2005', 'db_server_name', 'db_user', 'db_password']
    db_name='' 
    db_user=''
    db_password=''
    userdb = "-E"
    username='Administrateur'
    remote_backup_dir =  r'c:/WINDOWS/Temp/'
    sqlserver_before_2005 = False
    db_server_name = "localhost"
    

    def do_backup(self,stats):

        try:
            mykey = paramiko.RSAKey.from_private_key_file(self.private_key)
        except paramiko.SSHException:
            mykey = paramiko.DSSKey.from_private_key_file(self.private_key)
        
        self.logger.debug('[%s] Connecting to %s with user root and key %s',self.backup_name,self.server_name,self.private_key)
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.server_name,username=self.username,pkey=mykey, port=self.ssh_port)

        t = datetime.datetime.now()
        backup_start_date =  t.strftime('%Y%m%d-%Hh%Mm%S')
        
        backup_file = self.remote_backup_dir + '/' + self.db_name  + '-' + backup_start_date + '.bak'
    	if not self.db_user == '':
	   self.userdb = '-U %s -P %s' % ( self.db_user, self.db_password )

        # dump db
        stats['status']='Dumping'
	if self.sqlserver_before_2005:
		cmd =  """osql -E -Q "BACKUP DATABASE [%s] 
				      TO DISK='%s' 
				      WITH FORMAT" """ % ( self.db_name, backup_file )
	
	else:
        	cmd =  """sqlcmd %s -S "%s" -d master -Q "BACKUP DATABASE [%s] 
                	                                       TO DISK = N'%s' 
                        	                               WITH INIT, NOUNLOAD , 
                                	                       NAME = N'Backup %s', NOSKIP ,STATS = 10, NOFORMAT" """ % (self.userdb, self.db_server_name, self.db_name, backup_file ,self.db_name )
        self.logger.debug('[%s] Dump DB : %s',self.backup_name,cmd)
        try:
            if not self.dry_run:
                (error_code,output) = ssh_exec(cmd,ssh=ssh)
                self.logger.debug("[%s] Output of %s :\n%s",self.backup_name,cmd,output)
                if error_code:
                    raise Exception('Aborting, Not null exit code (%i) for "%s"' % (error_code,cmd))
    
            # zip the file
            stats['status']='Zipping'
            cmd = 'gzip "%s"' % backup_file
            self.logger.debug('[%s] Compress backup : %s',self.backup_name,cmd)
            if not self.dry_run:
                (error_code,output) = ssh_exec(cmd,ssh=ssh)
                self.logger.debug("[%s] Output of %s :\n%s",self.backup_name,cmd,output)
                if error_code:
                    raise Exception('Aborting, Not null exit code (%i) for "%s"' % (error_code,cmd))
    
            # get the file
            stats['status']='SFTP'
            filepath = backup_file + '.gz'
            localpath = os.path.join(self.backup_dir , self.db_name + '-' + backup_start_date + '.bak.gz')
            self.logger.debug('[%s] Get gz backup with sftp on %s from %s to %s',self.backup_name,self.server_name,filepath,localpath)
            if not self.dry_run:
                transport =  ssh.get_transport()
                sftp = paramiko.SFTPClient.from_transport(transport)
                sftp.get(filepath, localpath)
                sftp.close()
    
            if not self.dry_run:
                stats['total_files_count']=1
                stats['written_files_count']=1
                stats['total_bytes']=os.stat(localpath).st_size
                stats['written_bytes']=os.stat(localpath).st_size    
            stats['log']='gzip dump of DB %s:%s (%d bytes) to %s' % (self.server_name,self.db_name, stats['written_bytes'], localpath)
            stats['backup_location'] = localpath
            
        finally:
            stats['status']='RMTemp'
            cmd = 'rm -f "%s" "%s"' % ( backup_file + '.gz', backup_file )
            self.logger.debug('[%s] Remove temp gzip : %s',self.backup_name,cmd)
            if not self.dry_run:
                (error_code,output) = ssh_exec(cmd,ssh=ssh)
                self.logger.debug("[%s] Output of %s :\n%s",self.backup_name,cmd,output)
                if error_code:
                    raise Exception('Aborting, Not null exit code (%i) for "%s"' % (error_code,cmd))            
            

        
        stats['status']='OK'

    def register_existingbackups(self):
        """scan backup dir and insert stats in database"""

        registered = [b['backup_location'] for b in self.dbstat.query('select distinct backup_location from stats where backup_name=?',(self.backup_name,))]

        filelist = os.listdir(self.backup_dir)
        filelist.sort()
        p = re.compile('^%s-(?P<date>\d{8,8}-\d{2,2}h\d{2,2}m\d{2,2}).bak.gz$' % self.db_name) 
        for item in filelist:
            sr = p.match(item)
            if sr:
                file_name = os.path.join(self.backup_dir,item)
                start = datetime.datetime.strptime(sr.groups()[0],'%Y%m%d-%Hh%Mm%S').isoformat()
                if not file_name in registered:
                    self.logger.info('Registering %s from %s',file_name,fileisodate(file_name))
                    size_bytes = int(os.popen('du -sb "%s"' % file_name).read().split('\t')[0])
                    self.logger.debug('  Size in bytes : %i',size_bytes)
                    if not self.dry_run:        
                        self.dbstat.add(self.backup_name,self.server_name,'',\
                                        backup_start=start,backup_end=fileisodate(file_name),status='OK',total_bytes=size_bytes,backup_location=file_name)
                else:
                    self.logger.info('Skipping %s from %s, already registered',file_name,fileisodate(file_name))

register_driver(backup_sqlserver)
