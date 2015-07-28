#!/usr/bin/python
# -*- coding: utf-8 -*-
import subprocess
import os

backups = [ "ns3-test-etc-bind"]
backup_base_dir = "/backup/data/"
backup_retention_time=60



if not os.path.isdir("/backup/data/empty/"):
  os.mkdir("/backup/data/empty/")
for backup in backups:
    base_dir = os.path.join(backup_base_dir,backup)
    dest_dir = os.path.join(base_dir, 'last_backup')
    if not os.path.isdir(dest_dir):              
        cmd = "/sbin/btrfs subvolume create %s"%dest_dir
        print 'btrfs subvolume create "%s"' %dest_dir
        print subprocess.check_output(cmd, shell=True)

    if  len(os.listdir(dest_dir)) == 0:
	list_backups  =  sorted([os.path.join(base_dir, f) for f in os.listdir(base_dir)], key=os.path.getctime)
	recent_backup  =  list_backups[-2]
	print "The most recent backup : " + recent_backup
 	print "Initial copy"
	#cmd =  'rsync -rt --stats --delete-excluded --numeric-ids -P -lpgoD --protect-args  "%s"/ "%s"' % ( recent_backup, dest_dir)
	cmd =  'cp -v -a --reflink=always   "%s"/* "%s"' % ( recent_backup, dest_dir)
	print "Runinig %s " % cmd
        print subprocess.check_output(cmd, shell=True)
    if  len(os.listdir(base_dir)) > backup_retention_time:
	for folder in sorted([os.path.join(base_dir, f) for f in os.listdir(base_dir)], key=os.path.getctime)[0:len(os.listdir(base_dir)) -  (backup_retention_time )]:
		#cmd = 'rsync --dry-run -av --del /backup/data/empty/ "%s/"' % folder 
		cmd = 'rsync  -av --del /backup/data/empty/ "%s/"' % folder 
		print "Runinig %s " % cmd
        	print subprocess.check_output(cmd, shell=True)
		os.rmdir(folder)
	

