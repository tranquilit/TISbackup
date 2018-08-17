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

from common import *

class backup_pgsql(backup_generic):
    """Backup a postgresql database as gzipped sql file through ssh"""
    type = 'pgsql+ssh'
    required_params = backup_generic.required_params + ['private_key']
    optional_params = backup_generic.optional_params + ['db_name','tmp_dir','encoding']

    db_name = ''
    tmp_dir = '/tmp'
    encoding = 'UTF8'

    def do_backup(self,stats):
        self.dest_dir = os.path.join(self.backup_dir,self.backup_start_date)

        if not os.path.isdir(self.dest_dir):
            if not self.dry_run:
                os.makedirs(self.dest_dir)
            else:
                print 'mkdir "%s"' % self.dest_dir
        else:
            raise Exception('backup destination directory already exists : %s' % self.dest_dir)

        try:
            mykey = paramiko.RSAKey.from_private_key_file(self.private_key)
        except paramiko.SSHException:
            mykey = paramiko.DSSKey.from_private_key_file(self.private_key)

        self.logger.debug('[%s] Trying to connect to "%s" with username root and key "%s"',self.backup_name,self.server_name,self.private_key)
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.server_name,username='root',pkey = mykey,port=self.ssh_port)


        if  self.db_name:
            stats['log']= "Successfully backup processed to the following database :"
            self.do_pgsqldump(stats)
        else:
            stats['log']= "Successfully backuping processed to the following databases :"
            stats['status']='List'
            cmd = """su -  postgres -c 'psql -A -t  -c "SELECT datname FROM pg_database WHERE datistemplate = false;"' 2> /dev/null"""
            self.logger.debug('[%s] List databases: %s',self.backup_name,cmd)
            (error_code,output) = ssh_exec(cmd,ssh=self.ssh)
            self.logger.debug("[%s] Output of %s :\n%s",self.backup_name,cmd,output)
            if error_code:
                raise Exception('Aborting, Not null exit code (%i) for "%s"' % (error_code,cmd))
            databases = output.split('\n')
            for database in databases:
                if database.strip() not in ("", "template0", "template1"):
                    self.db_name = database.strip()
                    self.do_pgsqldump(stats)


        stats['status']='OK'


    def do_pgsqldump(self,stats):
        t = datetime.datetime.now()
        backup_start_date =  t.strftime('%Y%m%d-%Hh%Mm%S')
        params =  {
            'encoding':self.encoding,
            'db_name':self.db_name,
            'tmp_dir':self.tmp_dir,
            'dest_dir':self.dest_dir,
            'backup_start_date':backup_start_date}
        # dump db
        filepath = '%(tmp_dir)s/%(db_name)s-%(backup_start_date)s.sql.gz' % params
        cmd = "su -  postgres -c 'pg_dump -E %(encoding)s -Z9 %(db_name)s'" % params
        cmd += ' > ' + filepath
        self.logger.debug('[%s] %s ',self.backup_name,cmd)
        if not self.dry_run:
            (error_code,output) = ssh_exec(cmd,ssh=self.ssh)
            self.logger.debug("[%s] Output of %s :\n%s",self.backup_name,cmd,output)
            if error_code:
                raise Exception('Aborting, Not null exit code (%i) for "%s"' % (error_code,cmd))

        # get the file
        localpath = '%(dest_dir)s/%(db_name)s-%(backup_start_date)s.sql.gz' % params
        self.logger.debug('[%s] get the file using sftp from "%s" to "%s" ',self.backup_name,filepath,localpath)
        if not self.dry_run:
            transport =  self.ssh.get_transport()
            sftp = paramiko.SFTPClient.from_transport(transport)
            sftp.get(filepath, localpath)
            sftp.close()

        if not self.dry_run:
            stats['total_files_count']=1 + stats.get('total_files_count', 0)
            stats['written_files_count']=1 + stats.get('written_files_count', 0)
            stats['total_bytes']=os.stat(localpath).st_size + stats.get('total_bytes', 0)
            stats['written_bytes']=os.stat(localpath).st_size  +  stats.get('written_bytes', 0)
        stats['log'] = '%s "%s"' % (stats['log'] ,self.db_name)
        stats['backup_location'] = self.dest_dir

        cmd = 'rm -f %(tmp_dir)s/%(db_name)s-%(backup_start_date)s.sql.gz' % params
        self.logger.debug('[%s] %s ',self.backup_name,cmd)
        if not self.dry_run:
            (error_code,output) = ssh_exec(cmd,ssh=self.ssh)
            self.logger.debug("[%s] Output of %s :\n%s",self.backup_name,cmd,output)
            if error_code:
                raise Exception('Aborting, Not null exit code (%i) for "%s"' % (error_code,cmd))



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

register_driver(backup_pgsql)
