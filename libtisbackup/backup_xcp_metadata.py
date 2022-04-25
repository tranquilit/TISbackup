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



from .common import *
import paramiko

class backup_xcp_metadata(backup_generic):
    """Backup metatdata of a xcp pool using xe pool-dump-database"""
    type = 'xcp-dump-metadata'    
    required_params = ['type','server_name','private_key','backup_name']

    def do_backup(self,stats):

        self.logger.debug('[%s] Connecting to %s with user root and key %s',self.backup_name,self.server_name,self.private_key)


        t = datetime.datetime.now()
        backup_start_date = t.strftime('%Y%m%d-%Hh%Mm%S')

        # dump pool medatadata
        localpath = os.path.join(self.backup_dir ,  'xcp_metadata-' + backup_start_date + '.dump')
        stats['status']='Dumping'
        if not self.dry_run:
            cmd = "/opt/xensource/bin/xe pool-dump-database file-name="
            self.logger.debug('[%s] Dump XCP Metadata : %s', self.backup_name, cmd)
            (error_code, output) = ssh_exec(cmd, server_name=self.server_name,private_key=self.private_key, remote_user='root')

            with open(localpath,"w") as f:
                f.write(output)

        # zip the file
        stats['status']='Zipping'
        cmd = 'gzip %s '  % localpath
        self.logger.debug('[%s] Compress backup : %s',self.backup_name,cmd)
        if not self.dry_run:
            call_external_process(cmd)
        localpath += ".gz"
        if not self.dry_run:
            stats['total_files_count']=1
            stats['written_files_count']=1
            stats['total_bytes']=os.stat(localpath).st_size
            stats['written_bytes']=os.stat(localpath).st_size    
        stats['log']='gzip dump of DB %s:%s (%d bytes) to %s' % (self.server_name,'xcp metadata dump', stats['written_bytes'], localpath)
        stats['backup_location'] = localpath
        stats['status']='OK'



    def register_existingbackups(self):
        """scan metatdata backup files and insert stats in database"""

        registered = [b['backup_location'] for b in self.dbstat.query('select distinct backup_location from stats where backup_name=?',(self.backup_name,))]

        filelist = os.listdir(self.backup_dir)
        filelist.sort()
        p = re.compile('^%s-(?P<date>\d{8,8}-\d{2,2}h\d{2,2}m\d{2,2}).dump.gz$' % self.server_name) 
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

register_driver(backup_xcp_metadata)
