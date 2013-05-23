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
import time

class backup_rdiff:
  backup_dir=''
  backup_start_date=None
  backup_name=''
  server_name=''
  exclude_list=''
  ssh_port='22' 
  remote_user='root'
  remote_dir=''
  dest_dir=''
  verbose = False
  dry_run=False



  def __init__(self, backup_name, backup_base_dir):
    self.backup_dir = backup_base_dir + '/' + backup_name

    if os.path.isdir(self.backup_dir )==False:
      os.makedirs(self.backup_dir)
 
    self.backup_name = backup_name
    t = datetime.datetime.now()
    self.backup_start_date = t.strftime('%Y%m%d-%Hh%Mm%S')

  def get_latest_backup(self):
    filelist = os.listdir(self.backup_dir)
    if len(filelist) == 0:
      return ''

    filelist.sort()
    
    return filelist[-1]

  def cleanup_backup(self):
    filelist = os.listdir(self.backup_dir)
    if len(filelist) == 0:
      return ''

    filelist.sort()
    for backup_date in filelist:
      today = time.time()
      print backup_date
      datestring =  backup_date[0:8] 
      c = time.strptime(datestring,"%Y%m%d")
      # TODO: improve
      if today - c < 60 * 60 * 24* 30:
        print time.strftime("%Y%m%d",c) + " is to be deleted"


  def copy_latest_to_new(self):
    # TODO check that latest exist
    # TODO check that new does not exist


    last_backup =  self.get_latest_backup()
    if last_backup=='':
      print "*********************************"
      print "*first backup for " + self.backup_name
    else:
      latest_backup_path = self.backup_dir + '/' + last_backup 
      new_backup_path = self.backup_dir + '/' + self.backup_start_date
      print "#cp -al starting"
      cmd = 'cp -al ' + latest_backup_path + ' ' + new_backup_path
      print cmd
      if self.dry_run==False:
        call_external_process(cmd)
      print "#cp -al finished"
    

  def rsync_to_new(self):

    self.dest_dir = self.backup_dir + '/' + self.backup_start_date + '/'
    src_server = self.remote_user + '@' + self.server_name + ':"' + self.remote_dir.strip() + '/"'

    print "#starting rsync"
    verbose_arg=""
    if self.verbose==True:
      verbose_arg = "-P "
    
    cmd = "rdiff-backup " + verbose_arg + ' --compress-level=9 --numeric-ids -az --partial -e "ssh -o StrictHostKeyChecking=no -c Blowfish -p ' + self.ssh_port + ' -i ' + self.private_key + '" --stats --delete-after ' + self.exclude_list + ' ' + src_server + ' ' + self.dest_dir 
    print cmd

    ## deal with exit code 24 (file vanished)
    if self.dry_run==False:
      p = subprocess.call(cmd, shell=True)
      if (p ==24):
        print "Note: some files vanished before transfer"
      if (p != 0 and p != 24 ):
        raise Exception('shell program exited with error code ' + str(p), cmd)


    print "#finished rsync"

  def process_backup(self):
    print ""
    print "#========Starting backup item ========="
    self.copy_latest_to_new()

    self.rsync_to_new()     
    print "#========Backup item finished=========="


