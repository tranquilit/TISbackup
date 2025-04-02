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

import os
import datetime
from .common import *
import time
import logging
import re
import os.path
import datetime
from .common import *


class backup_rsync_btrfs(backup_generic):
    """Backup a directory on remote server with rsync and btrfs protocol (requires running remote rsync daemon)"""
    type = 'rsync+btrfs'       
    required_params = backup_generic.required_params + ['remote_user','remote_dir','rsync_module','password_file']
    optional_params = backup_generic.optional_params + ['compressionlevel','compression','bwlimit','exclude_list','protect_args','overload_args']

    remote_user='root'
    remote_dir=''

    exclude_list=''
    rsync_module=''
    password_file = ''
    compression = ''
    bwlimit = 0
    protect_args = '1'
    overload_args = None
    compressionlevel = 0

    

    def read_config(self,iniconf):
        assert(isinstance(iniconf,ConfigParser))
        backup_generic.read_config(self,iniconf)
        if not self.bwlimit and iniconf.has_option('global','bw_limit'):
            self.bwlimit = iniconf.getint('global','bw_limit')
        if not self.compressionlevel and iniconf.has_option('global','compression_level'):
            self.compressionlevel = iniconf.getint('global','compression_level') 

    def do_backup(self,stats):
        if not self.set_lock():
            self.logger.error("[%s] a lock file is set, a backup maybe already running!!",self.backup_name)
            return False

        try:
            try:
                backup_source = 'undefined'
                dest_dir = os.path.join(self.backup_dir,'last_backup')
                if not os.path.isdir(dest_dir):
                    if not self.dry_run:
                        cmd = "/bin/btrfs subvolume create %s"%dest_dir
                        process = subprocess.Popen(cmd, shell=True,  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
                        log = monitor_stdout(process,'',self)
                        returncode = process.returncode
                        if (returncode != 0):
                            self.logger.error("[" + self.backup_name + "] shell program exited with error code: %s"%log)
                            raise Exception("[" + self.backup_name + "] shell program exited with error code " + str(returncode), cmd)                      
                        else:
                            self.logger.info("[" + self.backup_name + "] create btrs volume: %s"%dest_dir)
                    else:
                        print(('btrfs subvolume create "%s"' %dest_dir))

                options = ['-rt', '--stats', '--delete-excluded', '--numeric-ids', '--delete-after', '--partial']

                if self.logger.level == logging.DEBUG:
                    self.logger.warning(f"[{self.backup_name}] Note that stdout cannot be entire if it contains too much data and the server doesn't have enough RAM !")
                    options.append('--progress')

                if self.dry_run:
                    options.append('-d')

                if self.overload_args != None:
                    options.append(self.overload_args)
                elif not "cygdrive" in self.remote_dir:
                    # we don't preserve owner, group, links, hardlinks, perms for windows/cygwin as it is not reliable nor useful
                    options.append('-lpgoD')

                # the protect-args option is not available in all rsync version
                if not self.protect_args.lower() in ('false','no','0'):
                    options.append('--protect-args')

                if self.compression.lower() in ('true','yes','1'):
                    options.append('-z')

                if self.compressionlevel:
                    options.append('--compress-level=%s' % self.compressionlevel)

                if self.bwlimit:
                    options.append('--bwlimit %s' % self.bwlimit)

                latest = self.get_latest_backup(self.backup_start_date)
                #remove link-dest replace by btrfs
                #if latest:
                #    options.extend(['--link-dest="%s"' % os.path.join('..',b,'') for b in latest])

                def strip_quotes(s):
                    if s[0] == '"':
                        s = s[1:]
                    if s[-1] == '"':
                        s = s[:-1]
                    return s

                # Add excludes
                if "--exclude" in self.exclude_list:
                    # old settings with exclude_list=--exclude toto --exclude=titi
                    excludes = [strip_quotes(s).strip() for s in self.exclude_list.replace('--exclude=','').replace('--exclude ','').split()]
                else:
                    try:
                        # newsettings with exclude_list='too','titi', parsed as a str python list content
                        excludes = eval('[%s]' % self.exclude_list)
                    except Exception as e:
                        raise Exception('Error reading exclude list : value %s, eval error %s (don\'t forget quotes and comma...)' % (self.exclude_list,e))
                options.extend(['--exclude="%s"' % x for x in excludes])

                if (self.rsync_module and not self.password_file):
                    raise Exception('You must specify a password file if you specify a rsync module')

                if (not self.rsync_module and not self.private_key):
                    raise Exception('If you don''t use SSH, you must specify a rsync module')

                #rsync_re = re.compile('(?P<server>[^:]*)::(?P<export>[^/]*)/(?P<path>.*)')
                #ssh_re = re.compile('((?P<user>.*)@)?(?P<server>[^:]*):(?P<path>/.*)')

                # Add ssh connection params
                if self.rsync_module:
                    # Case of rsync exports
                    if self.password_file:
                        options.append('--password-file="%s"' % self.password_file)
                    backup_source = '%s@%s::%s%s' % (self.remote_user, self.server_name, self.rsync_module, self.remote_dir)
                else:
                    # case of rsync + ssh
                    ssh_params = ['-o StrictHostKeyChecking=no']
                    if self.private_key:
                        ssh_params.append('-i %s' % self.private_key)
                    if self.cipher_spec:
                        ssh_params.append('-c %s' % self.cipher_spec)
                    if self.ssh_port != 22:
                        ssh_params.append('-p %i' % self.ssh_port)
                    options.append('-e "/usr/bin/ssh %s"' % (" ".join(ssh_params)))
                    backup_source = '%s@%s:%s' % (self.remote_user,self.server_name,self.remote_dir)

                # ensure there is a slash at end
                if backup_source[-1] != '/':
                    backup_source += '/'

                options_params = " ".join(options)

                cmd = '/usr/bin/rsync %s %s %s 2>&1' % (options_params,backup_source,dest_dir)
                self.logger.debug("[%s] rsync : %s",self.backup_name,cmd)

                if not self.dry_run:
                    self.line = ''
                    process = subprocess.Popen(cmd, shell=True,  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
                    def ondata(data,context):
                        if context.verbose:
                            print(data)
                        context.logger.debug(data)

                    log = monitor_stdout(process,ondata,self)

                    reg_total_files = re.compile('Number of files: (?P<file>\d+)')
                    reg_transferred_files = re.compile('Number of .*files transferred: (?P<file>\d+)')
                    for l in log.splitlines():
                        line = l.replace(',','').replace('.','')
                        m = reg_total_files.match(line)
                        if m:
                            stats['total_files_count'] += int(m.groupdict()['file'])
                        m = reg_transferred_files.match(line)
                        if m:
                            stats['written_files_count'] += int(m.groupdict()['file'])
                        if line.startswith('Total file size:'):
                            stats['total_bytes'] += int(line.split(':')[1].split()[0])
                        if line.startswith('Total transferred file size:'):
                            stats['written_bytes'] += int(line.split(':')[1].split()[0])

                    returncode = process.returncode
                    ## deal with exit code 24 (file vanished)
                    if (returncode == 24):
                        self.logger.warning("[" + self.backup_name + "] Note: some files vanished before transfer")
                    elif (returncode == 23):
                        self.logger.warning("[" + self.backup_name + "] unable so set uid on some files")
                    elif (returncode != 0):
                        self.logger.error("[" + self.backup_name + "] shell program exited with error code ", str(returncode))
                        raise Exception("[" + self.backup_name + "] shell program exited with error code " + str(returncode), cmd, log[-512:])
                else:
                    print(cmd)

                #we take a snapshot of last_backup if everything went well
                finaldest = os.path.join(self.backup_dir,self.backup_start_date)
                self.logger.debug("[%s] snapshoting last_backup directory from %s to %s" ,self.backup_name,dest_dir,finaldest)
                if not os.path.isdir(finaldest):
                    if not self.dry_run:
                        cmd = "/bin/btrfs subvolume snapshot %s %s"%(dest_dir,finaldest)
                        process = subprocess.Popen(cmd, shell=True,  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
                        log = monitor_stdout(process,'',self)
                        returncode = process.returncode
                        if (returncode != 0):
                            self.logger.error("[" + self.backup_name + "] shell program exited with error code " + str(returncode))
                            raise Exception("[" + self.backup_name + "] shell program exited with error code " + str(returncode), cmd, log[-512:])
                        else:
                            self.logger.info("[" + self.backup_name + "] snapshot directory created %s"%finaldest)
                    else:
                        print(("btrfs snapshot of %s to %s"%(dest_dir,finaldest)))
                else:
                    raise Exception('snapshot directory already exists : %s' %finaldest)
                self.logger.debug("[%s] touching datetime of target directory %s" ,self.backup_name,finaldest)
                print((os.popen('touch "%s"' % finaldest).read()))
                stats['backup_location'] = finaldest
                stats['status']='OK'
                stats['log']='ssh+rsync+btrfs backup from %s OK, %d bytes written for %d changed files' % (backup_source,stats['written_bytes'],stats['written_files_count'])

            except BaseException as e:
                stats['status']='ERROR'
                stats['log']=str(e)
                raise


        finally:  
            self.remove_lock()

    def get_latest_backup(self,current):
        result = []
        filelist = os.listdir(self.backup_dir)
        filelist.sort()
        filelist.reverse()
        full = ''
        r_full = re.compile('^\d{8,8}-\d{2,2}h\d{2,2}m\d{2,2}$') 
        r_partial = re.compile('^\d{8,8}-\d{2,2}h\d{2,2}m\d{2,2}.rsync$') 
        # we take all latest partials younger than the latest full and the latest full
        for item in filelist:
            if r_partial.match(item) and item<current:
                result.append(item)
            elif r_full.match(item) and item<current:
                result.append(item)
                break
        return result


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


    def is_pid_still_running(self,lockfile):
        f = open(lockfile)
        lines = f.readlines()
        f.close()
        if len(lines)==0 :
            self.logger.info("[" + self.backup_name + "] empty lock file, removing...")
            return False

        for line in lines:
            if line.startswith('pid='):
                pid = line.split('=')[1].strip()
                if os.path.exists("/proc/" + pid):
                    self.logger.info("[" + self.backup_name + "] process still there")
                    return True
                else:
                    self.logger.info("[" + self.backup_name + "] process not there anymore remove lock")
                    return False
            else:
                self.logger.info("[" + self.backup_name + "] incorrrect lock file : no pid line")
                return False	


    def set_lock(self):
        self.logger.debug("[" + self.backup_name + "] setting lock")

        #TODO: improve for race condition
        #TODO: also check if process is really there
        if os.path.isfile(self.backup_dir + '/lock'):
            self.logger.debug("[" + self.backup_name + "] File " + self.backup_dir + '/lock already exist')
            if self.is_pid_still_running(self.backup_dir + '/lock')==False:
                self.logger.info("[" + self.backup_name + "] removing lock file " + self.backup_dir + '/lock')
                os.unlink(self.backup_dir + '/lock')
            else:
                return False

        lockfile = open(self.backup_dir + '/lock',"w")
        # Write all the lines at once:
        lockfile.write('pid='+str(os.getpid()))
        lockfile.write('\nbackup_time=' + self.backup_start_date)
        lockfile.close()
        return True

    def remove_lock(self):
        self.logger.debug("[%s] removing lock",self.backup_name )
        os.unlink(self.backup_dir + '/lock')

class backup_rsync__btrfs_ssh(backup_rsync_btrfs):
    """Backup a directory on remote server with rsync,ssh and btrfs protocol (requires rsync software on remote host)"""
    type = 'rsync+btrfs+ssh'       
    required_params = backup_generic.required_params + ['remote_user','remote_dir','private_key']
    optional_params = backup_generic.optional_params + ['compression','bwlimit','ssh_port','exclude_list','protect_args','overload_args','cipher_spec']
    cipher_spec = ''


register_driver(backup_rsync_btrfs)
register_driver(backup_rsync__btrfs_ssh)

if __name__=='__main__':
    logger = logging.getLogger('tisbackup')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    cp = ConfigParser()
    cp.read('/opt/tisbackup/configtest.ini')
    dbstat = BackupStat('/backup/data/log/tisbackup.sqlite')
    b = backup_rsync('htouvet','/backup/data/htouvet',dbstat)
    b.read_config(cp)
    b.process_backup()
    print((b.checknagios()))

