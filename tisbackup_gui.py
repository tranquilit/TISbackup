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
import os,sys
from os.path import isfile, join
tisbackup_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.append(os.path.join(tisbackup_root_dir,'lib'))
sys.path.append(os.path.join(tisbackup_root_dir,'libtisbackup'))


from shutil import *
from iniparse import ConfigParser,RawConfigParser
from libtisbackup.common import *
import time 
from flask import request, Flask,  session, g, appcontext_pushed, redirect, url_for, abort, render_template, flash, jsonify, Response
from urllib.parse import urlparse
import json
import glob
import time

from config import huey
from tasks import run_export_backup, get_task, set_task

from tisbackup import tis_backup
import logging
import re


cp = ConfigParser()
cp.read("/etc/tis/tisbackup_gui.ini")

CONFIG = cp.get('general','config_tisbackup').split(",")
SECTIONS = cp.get('general','sections')
ADMIN_EMAIL = cp.get('general','ADMIN_EMAIL')
BASE_DIR = cp.get('general','base_config_dir')

tisbackup_config_file= CONFIG[0]
config_number=0

cp = ConfigParser()
cp.read(tisbackup_config_file)
backup_base_dir = cp.get('global','backup_base_dir')
dbstat = BackupStat(os.path.join(backup_base_dir,'log','tisbackup.sqlite'))
mindate = None
error = None
info = None
app = Flask(__name__)
app.secret_key = 'fsiqefiuqsefARZ4Zfesfe34234dfzefzfe'
app.config['PROPAGATE_EXCEPTIONS'] = True

tasks_db = os.path.join(tisbackup_root_dir,"tasks.sqlite")


def read_all_configs(base_dir):
    raw_configs = []
    list_config = []
    config_base_dir = base_dir
    
    for file in os.listdir(base_dir):
        if isfile(join(base_dir,file)): 
            raw_configs.append(join(base_dir,file))
    
    for elem in raw_configs:
        line = open(elem).readline()
        if 'global' in line:
            list_config.append(elem)

    backup_dict = {}
    backup_dict['rsync_ssh_list'] = []
    backup_dict['rsync_btrfs_list'] = []
    backup_dict['rsync_list'] = []
    backup_dict['null_list'] = []
    backup_dict['pgsql_list'] = []
    backup_dict['mysql_list'] = []
    #backup_dict['sqlserver_list'] = []
    backup_dict['xva_list'] = []
    backup_dict['metadata_list'] = []
    #backup_dict['switch_list'] = []
    #backup_dict['oracle_list'] = []

    result = []
    cp = ConfigParser()
    for config_file in list_config:
        cp.read(config_file)

        backup_base_dir = cp.get('global', 'backup_base_dir')
        backup = tis_backup(backup_base_dir=backup_base_dir)
        backup.read_ini_file(config_file)

        backup_sections = SECTIONS or []

        all_sections = [backup_item.backup_name for backup_item in backup.backup_list]
        if not backup_sections:
            backup_sections = all_sections
        else:
            for b in backup_sections:
                if not b in all_sections:
                    raise Exception('Section %s is not defined in config file' % b)

        if not backup_sections:
            sections = [backup_item.backup_name for backup_item in backup.backup_list]

        for backup_item in backup.backup_list:
            if backup_item.backup_name in backup_sections:
                b = {}
                for attrib_name in backup_item.required_params + backup_item.optional_params:
                    if hasattr(backup_item, attrib_name):
                        b[attrib_name] = getattr(backup_item, attrib_name)
                result.append(b)

    for row in result:
        backup_name = row['backup_name']
        server_name = row['server_name']
        backup_type = row['type']
        if backup_type == "xcp-dump-metadata":
            backup_dict['metadata_list'].append(
                [server_name, backup_name, backup_type, ""])
        if backup_type == "rsync+ssh":
            remote_dir = row['remote_dir']
            backup_dict['rsync_ssh_list'].append(
                [server_name, backup_name, backup_type, remote_dir])
        if backup_type == "rsync+btrfs+ssh":
            remote_dir = row['remote_dir']
            backup_dict['rsync_btrfs_list'].append(
                [server_name, backup_name, backup_type, remote_dir])
        if backup_type == "rsync":
            remote_dir = row['remote_dir']
            backup_dict['rsync_list'].append(
                [server_name, backup_name, backup_type, remote_dir])
        if backup_type == "null":
            backup_dict['null_list'].append(
                [server_name, backup_name, backup_type, ""])
        if backup_type == "pgsql+ssh":
            db_name = row['db_name'] if len(row['db_name']) > 0 else '*'
            backup_dict['pgsql_list'].append(
                [server_name, backup_name, backup_type, db_name])
        if backup_type == "mysql+ssh":
            db_name = row['db_name'] if len(row['db_name']) > 0 else '*'
            backup_dict['mysql_list'].append(
                [server_name, backup_name, backup_type, db_name])
        # if backup_type == "sqlserver+ssh":
        #     db_name = row['db_name']
        #     backup_dict['sqlserver_list'].append(
        #         [server_name, backup_name, backup_type, db_name])
        # if backup_type == "oracle+ssh":
        #     db_name = row['db_name']
        #     backup_dict['oracle_list'].append(
        #         [server_name, backup_name, backup_type, db_name])
        if backup_type == "xen-xva":
            backup_dict['xva_list'].append(
                [server_name, backup_name, backup_type, ""])
        # if backup_type == "switch":
        #     backup_dict['switch_list'].append(
        #         [server_name, backup_name, backup_type, ""])
            
    return backup_dict


def read_config():
    config_file = CONFIG[config_number]
    cp = ConfigParser()
    cp.read(config_file)

    backup_base_dir = cp.get('global','backup_base_dir')
    backup = tis_backup(backup_base_dir=backup_base_dir)
    backup.read_ini_file(config_file)

    backup_sections = SECTIONS or []

    all_sections = [backup_item.backup_name for backup_item in backup.backup_list]
    if not backup_sections:
        backup_sections = all_sections
    else:
        for b in backup_sections:
            if not b in all_sections:
                raise Exception('Section %s is not defined in config file' % b)

    result = []
    if not backup_sections:
        sections = [backup_item.backup_name for backup_item in backup.backup_list]

    for backup_item in backup.backup_list:
        if backup_item.backup_name in backup_sections:
            b = {}
            for attrib_name in backup_item.required_params+backup_item.optional_params:
                if hasattr(backup_item,attrib_name):
                    b[attrib_name] = getattr(backup_item,attrib_name)
            result.append(b)

    backup_dict = {}
    backup_dict['rsync_ssh_list'] = []
    backup_dict['rsync_btrfs_list'] = []
    backup_dict['rsync_list'] = []
    backup_dict['null_list'] = []
    backup_dict['pgsql_list'] = []
    backup_dict['mysql_list'] = []
    #backup_dict['sqlserver_list'] = []
    backup_dict['xva_list'] = []
    backup_dict['metadata_list'] = []
    #backup_dict['switch_list'] = []
    #backup_dict['oracle_list'] = []
    for row in result:
        backup_name = row['backup_name']
        server_name = row['server_name']
        backup_type = row['type']
        if backup_type == "xcp-dump-metadata":
            backup_dict['metadata_list'].append([server_name, backup_name, backup_type, ""])
        if backup_type == "rsync+ssh":
            remote_dir = row['remote_dir']
            backup_dict['rsync_ssh_list'].append([server_name, backup_name, backup_type,remote_dir])
        if backup_type == "rsync+btrfs+ssh":
            remote_dir = row['remote_dir']
            backup_dict['rsync_btrfs_list'].append([server_name, backup_name, backup_type,remote_dir])
        if backup_type == "rsync":
            remote_dir = row['remote_dir']
            backup_dict['rsync_list'].append([server_name, backup_name, backup_type,remote_dir])
        if backup_type == "null":
            backup_dict['null_list'].append([server_name, backup_name, backup_type, ""])
        if backup_type == "pgsql+ssh":
            db_name = row['db_name'] if len(row['db_name']) > 0 else '*'
            backup_dict['pgsql_list'].append([server_name, backup_name, backup_type, db_name])
        if backup_type == "mysql+ssh":
            db_name = row['db_name'] if len(row['db_name']) > 0 else '*'
            backup_dict['mysql_list'].append([server_name, backup_name, backup_type, db_name])
        # if backup_type == "sqlserver+ssh":
        #     db_name = row['db_name']
        #     backup_dict['sqlserver_list'].append([server_name, backup_name, backup_type, db_name])
        # if backup_type == "oracle+ssh":
        #     db_name = row['db_name']
        #     backup_dict['oracle_list'].append([server_name, backup_name, backup_type, db_name])
        if backup_type == "xen-xva":
            backup_dict['xva_list'].append([server_name, backup_name, backup_type, ""])
        # if backup_type == "switch":
        #     backup_dict['switch_list'].append([server_name, backup_name, backup_type, ""])
    return backup_dict

@app.route('/')
def backup_all():
    backup_dict = read_config()
    return render_template('backups.html', backup_list = backup_dict)


@app.route('/config_number/')
@app.route('/config_number/<int:id>')
def set_config_number(id=None):
    if id != None and  len(CONFIG) > id:
        global config_number
        config_number=id
        read_config()
    return jsonify(configs=CONFIG,config_number=config_number)


@app.route('/all_json')
def backup_all_json():
    backup_dict = read_all_configs(BASE_DIR)
    return json.dumps(backup_dict['rsync_list']+backup_dict['rsync_btrfs_list']+backup_dict['rsync_ssh_list']+backup_dict['pgsql_list']+backup_dict['mysql_list']+backup_dict['xva_list']+backup_dict['null_list']+backup_dict['metadata_list'])
    #+  backup_dict['switch_list'])+backup_dict['sqlserver_list']


@app.route('/json')
def backup_json():
    backup_dict = read_config()
    return json.dumps(backup_dict['rsync_list']+backup_dict['rsync_btrfs_list']+backup_dict['rsync_ssh_list']+backup_dict['pgsql_list']+backup_dict['mysql_list']+backup_dict['xva_list']+backup_dict['null_list']+backup_dict['metadata_list'])
    #+  backup_dict['switch_list'])+backup_dict['sqlserver_list']


def check_usb_disk():
    """This method returns the mounts point of FIRST external disk"""
#    disk_name = []
    usb_disk_list = []
    for name in glob.glob('/dev/sd[a-z]'):
        for line in os.popen("udevadm info -q env -n %s" % name):
            if re.match(r"ID_PATH=.*usb.*", line):
                usb_disk_list += [ name ]

    if len(usb_disk_list) == 0:
        raise_error("Cannot find any external usb disk", "You should plug the usb hard drive into the server")
        return ""
    print(usb_disk_list)

    usb_partition_list = []
    for usb_disk in usb_disk_list:
        cmd = "udevadm  info -q path -n %s" % usb_disk  + '1'
        output =  os.popen(cmd).read()
        print("cmd : " + cmd)
        print("output : " + output)

        if '/devices/pci'  in  output:
            #flash("partition found: %s1" % usb_disk)
            usb_partition_list.append(usb_disk + "1")

    print(usb_partition_list)

    if len(usb_partition_list) ==0:
        raise_error("The drive %s has no partition" % (usb_disk_list[0] ), "You should initialize the usb drive and format an ext4 partition with TISBACKUP label")
        return ""    

    tisbackup_partition_list = []
    for usb_partition in usb_partition_list:
        if "tisbackup" in os.popen("/sbin/dumpe2fs -h %s 2>&1 |/bin/grep 'volume name'" % usb_partition).read().lower():
            flash("tisbackup backup partition found: %s" % usb_partition)
            tisbackup_partition_list.append(usb_partition)

    print(tisbackup_partition_list)    

    if len(tisbackup_partition_list) ==0:
        raise_error("No tisbackup partition exist on disk %s" % (usb_disk_list[0] ), "You should initialize the usb drive and format an ext4 partition with TISBACKUP label")
        return ""

    if  len(tisbackup_partition_list) > 1:
        raise_error("There are many usb disk", "You should plug remove one of them")
        return ""


    return tisbackup_partition_list[0]


def check_already_mount(partition_name,refresh):
    with  open('/proc/mounts') as f:
        mount_point = ""
        for line in f.readlines():
            if line.startswith(partition_name):
                mount_point = line.split(' ')[1]     
            if not refresh:
                run_command("/bin/umount %s" % mount_point)
                os.rmdir(mount_point)                   
    return mount_point

def run_command(cmd, info=""):
    flash("Executing: %s"% cmd)
    from subprocess import CalledProcessError, check_output  
    result =""
    try:
        result = check_output(cmd, stderr=subprocess.STDOUT,shell=True)
    except CalledProcessError as e:
        raise_error(result,info)
    return result

def check_mount_disk(partition_name, refresh):       
    
    mount_point =  check_already_mount(partition_name, refresh)
    if not refresh:
                                    

        mount_point = "/mnt/TISBACKUP-" +str(time.time())
        os.mkdir(mount_point)
        flash("must mount " + partition_name )
        cmd = "mount %s %s" % (partition_name, mount_point)
        if run_command(cmd,"You should manualy mount the usb drive") != "":            
            flash("Remove directory: %s" % mount_point)
            os.rmdir(mount_point)   
            return ""        

    return mount_point

@app.route('/status.json')
def export_backup_status():
    exports = dbstat.query('select * from stats where TYPE="EXPORT" and backup_start>="%s"' % mindate)
    error = ""
    finish=not runnings_backups()
    if  get_task() != None and finish:
        status = get_task().get()
        if status != "ok":
            error = "Export failing with error: "+status

    
    return jsonify(data=exports,finish=finish,error=error)

def runnings_backups():
    task  = get_task()
    is_runnig = (task != None)
    finish = ( is_runnig and task.get() != None)
    return is_runnig and not finish


@app.route('/backups.json')
def last_backup_json():
    exports = dbstat.query('select * from stats where TYPE="BACKUP" ORDER BY backup_start DESC  ')
    return Response(response=json.dumps(exports),
                    status=200,
                    mimetype="application/json")


@app.route('/last_backups')
def last_backup():
    exports = dbstat.query('select * from stats where TYPE="BACKUP" ORDER BY backup_start DESC LIMIT 20 ')
    return render_template("last_backups.html", backups=exports)


@app.route('/export_backup')
def export_backup():
    
    raise_error("", "")
    backup_dict = read_config()
    sections = []
    backup_sections = []
    for  backup_types in backup_dict:
        if backup_types == "null_list":
            continue
        for section in backup_dict[backup_types]:
            #if section.count > 0:
            if len(section) > 0:
                sections.append(section[1])

    noJobs = (not runnings_backups())
    if "start" in list(request.args.keys()) or not noJobs:
        start=True
        if "sections" in list(request.args.keys()):
            backup_sections = request.args.getlist('sections')
        

    else:
        start=False
    cp.read(tisbackup_config_file)

    partition_name = check_usb_disk()
    if partition_name:
        if noJobs:
            mount_point = check_mount_disk( partition_name, False)
        else:
            mount_point = check_mount_disk( partition_name, True)
    if noJobs:
        global mindate 
        mindate =  datetime2isodate(datetime.datetime.now())
        if not error and start:
            print(tisbackup_config_file)
            task = run_export_backup(base=backup_base_dir, config_file=CONFIG[config_number], mount_point=mount_point, backup_sections=",".join([str(x) for x in backup_sections]))
            set_task(task)
		
            
    return render_template("export_backup.html", error=error, start=start, info=info, email=ADMIN_EMAIL, sections=sections)


def raise_error(strError, strInfo):
    global error, info
    error = strError
    info = strInfo


if __name__ == "__main__":    
    read_config()
    from os import environ
    if 'WINGDB_ACTIVE' in environ:
        app.debug = False
    app.run(host= '0.0.0.0',port=8080)
