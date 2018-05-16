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
import subprocess
from iniparse import ConfigParser
from optparse import OptionParser

import re
import sys
import getopt
import os.path
import logging
import errno
from libtisbackup.common import *
from libtisbackup.backup_mysql import backup_mysql
from libtisbackup.backup_rsync import backup_rsync
from libtisbackup.backup_rsync import backup_rsync_ssh
from libtisbackup.backup_oracle import backup_oracle
from libtisbackup.backup_rsync_btrfs import backup_rsync_btrfs
from libtisbackup.backup_rsync_btrfs import backup_rsync__btrfs_ssh
from libtisbackup.backup_pgsql import backup_pgsql
from libtisbackup.backup_xva import backup_xva
from libtisbackup.backup_vmdk import backup_vmdk
from libtisbackup.backup_switch import backup_switch
from libtisbackup.backup_null import backup_null
from libtisbackup.backup_xcp_metadata import backup_xcp_metadata
from libtisbackup.copy_vm_xcp import copy_vm_xcp
from libtisbackup.backup_sqlserver import backup_sqlserver
from libtisbackup.backup_samba4 import backup_samba4

usage="""\
%prog -c configfile action

TIS Files Backup system.

action is either :
 backup : launch all backups or a specific one if -s option is used
 cleanup : removed backups older than retension period
 checknagios : check all or a specific backup against max_backup_age parameter
 dumpstat : dump the content of database for the last 20 backups
 retryfailed :  try to relaunch the last failed backups
 listdrivers :  list available backup types and parameters for config inifile
 exportbackup :  copy lastest OK backups from local to location defned by --exportdir parameter
 register_existing : scan backup directories and add missing backups to database"""

version="VERSION"

parser=OptionParser(usage=usage,version="%prog " + version)
parser.add_option("-c","--config", dest="config", default='/etc/tis/tisbackup-config.ini', help="Config file full path (default: %default)")
parser.add_option("-d","--dry-run",    dest="dry_run",    default=False, action='store_true', help="Dry run (default: %default)")
parser.add_option("-v","--verbose",    dest="verbose", default=False, action='store_true', help="More information (default: %default)")
parser.add_option("-s","--sections", dest="sections", default='', help="Comma separated list of sections (backups) to process (default: All)")
parser.add_option("-l","--loglevel", dest="loglevel", default='info', type='choice',  choices=['debug','warning','info','error','critical'], metavar='LOGLEVEL',help="Loglevel (default: %default)")
parser.add_option("-n","--len", dest="statscount", default=30, type='int', help="Number of lines to list for dumpstat (default: %default)")
parser.add_option("-b","--backupdir", dest="backup_base_dir", default='', help="Base directory for all backups (default: [global] backup_base_dir in config file)")
parser.add_option("-x","--exportdir", dest="exportdir", default='', help="Directory where to export latest backups with exportbackup (nodefault)")

class tis_backup:
    logger = logging.getLogger('tisbackup')

    def __init__(self,dry_run=False,verbose=False,backup_base_dir=''):
        self.dry_run = dry_run
        self.verbose = verbose
        self.backup_base_dir = backup_base_dir
        self.backup_base_dir = ''
        self.backup_list = []
        self.dry_run = dry_run
        self.verbose=False

    def read_ini_file(self,filename):
        cp = ConfigParser()
        cp.read(filename)

        if not self.backup_base_dir:
            self.backup_base_dir = cp.get('global','backup_base_dir')
        if not os.path.isdir(self.backup_base_dir):
            self.logger.info('Creating backup directory %s' % self.backup_base_dir)
            os.makedirs(self.backup_base_dir)

        self.logger.debug("backup directory : " + self.backup_base_dir)
        self.dbstat = BackupStat(os.path.join(self.backup_base_dir,'log','tisbackup.sqlite'))

        for section in cp.sections():
            if (section != 'global'):
                self.logger.debug("reading backup config " + section)
                backup_item = None
                type = cp.get(section,'type')

                backup_item = backup_drivers[type](backup_name=section,
                                                   backup_dir=os.path.join(self.backup_base_dir,section),dbstat=self.dbstat,dry_run=self.dry_run)
                backup_item.read_config(cp)
                backup_item.verbose = self.verbose

                self.backup_list.append(backup_item)

        # TODO check hostname socket.gethostbyname_ex('cnn.com')
        # TODO socket.gethostbyaddr('64.236.16.20')
        # TODO limit backup to one backup on the command line


    def checknagios(self,sections=[]):
        try:
            if not sections:
                sections = [backup_item.backup_name for backup_item in self.backup_list]

            self.logger.debug('Start of check nagios for %s' % (','.join(sections),))
            try:
                worst_nagiosstatus = None
                ok = []
                warning = []
                critical = []
                unknown = []
                nagiosoutput = ''
                for backup_item in self.backup_list:
                    if not sections or backup_item.backup_name in sections:
                        (nagiosstatus,log) = backup_item.checknagios()
                        if nagiosstatus == nagiosStateCritical:
                            critical.append((backup_item.backup_name,log))
                        elif nagiosstatus == nagiosStateWarning :
                            warning.append((backup_item.backup_name,log))
                        elif nagiosstatus == nagiosStateOk:
                            ok.append((backup_item.backup_name,log))
                        else:
                            unknown.append((backup_item.backup_name,log))
                        self.logger.debug('[%s] nagios:"%i" log: %s',backup_item.backup_name,nagiosstatus,log)

                if not ok and not critical and not unknown and not warning:
                    self.logger.debug('Nothing processed')
                    worst_nagiosstatus = nagiosStateUnknown
                    nagiosoutput = 'UNKNOWN : Unknown backup sections "%s"' % sections

                globallog = []

                if unknown:
                    if not worst_nagiosstatus:
                        worst_nagiosstatus = nagiosStateUnknown
                        nagiosoutput = 'UNKNOWN status backups %s' % (','.join([b[0] for b in unknown]))
                    globallog.extend(unknown)

                if critical:
                    if not worst_nagiosstatus:
                        worst_nagiosstatus = nagiosStateCritical
                        nagiosoutput = 'CRITICAL backups %s' % (','.join([b[0] for b in critical]))
                    globallog.extend(critical)

                if warning:
                    if not worst_nagiosstatus:
                        worst_nagiosstatus = nagiosStateWarning
                        nagiosoutput = 'WARNING backups %s' % (','.join([b[0] for b in warning]))
                    globallog.extend(warning)

                if ok:
                    if not worst_nagiosstatus:
                        worst_nagiosstatus = nagiosStateOk
                        nagiosoutput = 'OK backups %s' % (','.join([b[0] for b in ok]))
                    globallog.extend(ok)

                if worst_nagiosstatus == nagiosStateOk:
                    nagiosoutput = 'ALL backups OK %s' % (','.join(sections))


            except BaseException,e:
                worst_nagiosstatus = nagiosStateCritical
                nagiosoutput = 'EXCEPTION',"Critical : %s" % str(e)
                raise

        finally:
            self.logger.debug('worst nagios status :"%i"',worst_nagiosstatus)
            print '%s (tisbackup V%s)' %(nagiosoutput,version)
            print '\n'.join(["[%s]:%s" % (l[0],l[1]) for l in globallog])
            sys.exit(worst_nagiosstatus)

    def process_backup(self,sections=[]):
        processed = []
        errors = []
        if not sections:
            sections = [backup_item.backup_name for backup_item in self.backup_list]

        self.logger.info('Processing backup for %s' % (','.join(sections)) )
        for backup_item in self.backup_list:
            if not sections or backup_item.backup_name in sections:
                try:
                    assert(isinstance(backup_item,backup_generic))
                    self.logger.info('Processing [%s]',(backup_item.backup_name))
                    stats = backup_item.process_backup()
                    processed.append((backup_item.backup_name,stats))
                except BaseException,e:
                    self.logger.critical('Backup [%s] processed with error : %s',backup_item.backup_name,e)
                    errors.append((backup_item.backup_name,str(e)))
        if not processed and not errors:
            self.logger.critical('No backup properly finished or processed')
        else:
            if processed:
                self.logger.info('Backup processed : %s' , ",".join([b[0] for b in processed]))
            if errors:
                self.logger.error('Backup processed with errors: %s' , ",".join([b[0] for b in errors]))

    def export_backups(self,sections=[],exportdir=''):
        processed = []
        errors = []
        if not sections:
            sections = [backup_item.backup_name for backup_item in self.backup_list]

        self.logger.info('Exporting OK backups for %s to %s' % (','.join(sections),exportdir) )

        for backup_item in self.backup_list:
            if backup_item.backup_name in sections:
                try:
                    assert(isinstance(backup_item,backup_generic))
                    self.logger.info('Processing [%s]',(backup_item.backup_name))
                    stats = backup_item.export_latestbackup(destdir=exportdir)
                    processed.append((backup_item.backup_name,stats))
                except BaseException,e:
                    self.logger.critical('Export Backup [%s] processed with error : %s',backup_item.backup_name,e)
                    errors.append((backup_item.backup_name,str(e)))
        if not processed and not errors:
            self.logger.critical('No export backup properly finished or processed')
        else:
            if processed:
                self.logger.info('Export Backups processed : %s' , ",".join([b[0] for b in processed]))
            if errors:
                self.logger.error('Export Backups processed with errors: %s' , ",".join([b[0] for b in errors]))

    def retry_failed_backups(self,maxage_hours=30):
        processed = []
        errors = []

        # before mindate, backup is too old
        mindate = datetime2isodate((datetime.datetime.now() - datetime.timedelta(hours=maxage_hours)))
        failed_backups = self.dbstat.query("""\
        select  distinct backup_name as bname
        from stats
        where  status="OK"  and  backup_start>=?""",(mindate,))

        defined_backups =  map(lambda f:f.backup_name, [ x for x in self.backup_list if not isinstance(x, backup_null) ])
        failed_backups_names = set(defined_backups) - set([b['bname'] for b in failed_backups if b['bname'] in defined_backups])


        if failed_backups_names:
            self.logger.info('Processing backup for %s',','.join(failed_backups_names))
            for backup_item in self.backup_list:
                if backup_item.backup_name in failed_backups_names:
                    try:
                        assert(isinstance(backup_item,backup_generic))
                        self.logger.info('Processing [%s]',(backup_item.backup_name))
                        stats = backup_item.process_backup()
                        processed.append((backup_item.backup_name,stats))
                    except BaseException,e:
                        self.logger.critical('Backup [%s] not processed, error : %s',backup_item.backup_name,e)
                        errors.append((backup_item.backup_name,str(e)))
            if not processed and not errors:
                self.logger.critical('No backup properly finished or processed')
            else:
                if processed:
                    self.logger.info('Backup processed : %s' , ",".join([b[0] for b in errors]))
                if errors:
                    self.logger.error('Backup processed with errors: %s' , ",".join([b[0] for b in errors]))
        else:
            self.logger.info('No recent failed backups found in database')


    def cleanup_backup_section(self,sections = []):
        log = ''
        processed = False
        if not sections:
            sections = [backup_item.backup_name for backup_item in self.backup_list]

        self.logger.info('Processing cleanup for %s' % (','.join(sections)) )
        for backup_item in self.backup_list:
            if backup_item.backup_name in sections:
                try:
                    assert(isinstance(backup_item,backup_generic))
                    self.logger.info('Processing cleanup of [%s]',(backup_item.backup_name))
                    backup_item.cleanup_backup()
                    processed = True
                except BaseException,e:
                    self.logger.critical('Cleanup of [%s] not processed, error : %s',backup_item.backup_name,e)
        if not processed:
            self.logger.critical('No cleanup properly finished or processed')

    def register_existingbackups(self,sections = []):
        if not sections:
            sections = [backup_item.backup_name for backup_item in self.backup_list]

        self.logger.info('Append existing backups to database...')
        for backup_item in self.backup_list:
            if backup_item.backup_name in sections:
                backup_item.register_existingbackups()

    def html_report(self):
        for backup_item in self.backup_list:
            if not section or section == backup_item.backup_name:
                assert(isinstance(backup_item,backup_generic))
                if not maxage_hours:
                    maxage_hours = backup_item.maximum_backup_age
                (nagiosstatus,log) = backup_item.checknagios(maxage_hours=maxage_hours)
                globallog.append('[%s] %s' % (backup_item.backup_name,log))
                self.logger.debug('[%s] nagios:"%i" log: %s',backup_item.backup_name,nagiosstatus,log)
                processed = True
                if nagiosstatus >= worst_nagiosstatus:
                    worst_nagiosstatus = nagiosstatus


def main():
    (options,args)=parser.parse_args()

    if len(args) != 1:
        print "ERROR : You must provide one action to perform"
        parser.print_usage()
        sys.exit(2)

    backup_start_date = datetime.datetime.now().strftime('%Y%m%d-%Hh%Mm%S')

    # options
    action = args[0]
    if action == "listdrivers":
        for t in backup_drivers:
            print backup_drivers[t].get_help()
        sys.exit(0)

    config_file =options.config
    dry_run = options.dry_run
    verbose = options.verbose

    loglevel = options.loglevel

    # setup Logger
    logger = logging.getLogger('tisbackup')
    hdlr = logging.StreamHandler()
    hdlr.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(hdlr)

    # set loglevel
    if loglevel in ('debug','warning','info','error','critical'):
        numeric_level = getattr(logging, loglevel.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % loglevel)
        logger.setLevel(numeric_level)

    # Config file
    if not os.path.isfile(config_file):
        logger.error("Error : could not find file : " + config_file + ", please check the path")
    logger.info("Using " + config_file + " config file")

    cp = ConfigParser()
    cp.read(config_file)

    backup_base_dir = options.backup_base_dir or cp.get('global','backup_base_dir')
    log_dir = os.path.join(backup_base_dir,'log')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # if we run the nagios check, we don't create log file, everything is piped to stdout
    if action!='checknagios':
        try:
            hdlr = logging.FileHandler(os.path.join(log_dir,'tisbackup_%s.log' % (backup_start_date)))
            hdlr.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
            logger.addHandler(hdlr)
        except IOError, e:
            if action == 'cleanup' and e.errno == errno.ENOSPC:
                logger.warning("No space left on device, disabling file logging.")
            else:
                raise e

    # Main
    backup = tis_backup(dry_run=dry_run,verbose=verbose,backup_base_dir=backup_base_dir)
    backup.read_ini_file(config_file)

    backup_sections = options.sections.split(',') if options.sections else []

    all_sections = [backup_item.backup_name for backup_item in backup.backup_list]
    if not backup_sections:
        backup_sections = all_sections
    else:
        for b in backup_sections:
            if not b in all_sections:
                raise Exception('Section %s is not defined in config file' % b)

    if dry_run:
        logger.warning("WARNING : DRY RUN, nothing will be done, just printing on screen...")

    if action == "backup":
        backup.process_backup(backup_sections)
    elif action == "exportbackup":
        if not options.exportdir:
            raise Exception('No export directory supplied dor exportbackup action')
        backup.export_backups(backup_sections,options.exportdir)
    elif action == "cleanup":
        backup.cleanup_backup_section(backup_sections)
    elif action == "checknagios":
        backup.checknagios(backup_sections)
    elif action == "dumpstat":
        for s in backup_sections:
            backup.dbstat.last_backups(s,count=options.statscount)
    elif action == "retryfailed":
        backup.retry_failed_backups()
    elif action == "register_existing":
        backup.register_existingbackups(backup_sections)


    else:
        logger.error('Unhandled action "%s", quitting...',action)
        sys.exit(1)


if __name__ == "__main__":
    main()
