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
import subprocess
import re
import logging
import datetime
import time
from iniparse import ConfigParser
import sqlite3
import shutil
import select

import sys

try:
    sys.stderr = open('/dev/null')       # Silence silly warnings from paramiko
    import paramiko
except ImportError,e:
    print "Error : can not load paramiko library %s" % e
    raise

sys.stderr = sys.__stderr__

nagiosStateOk = 0
nagiosStateWarning = 1
nagiosStateCritical = 2
nagiosStateUnknown = 3

backup_drivers = {}
def register_driver(driverclass):
    backup_drivers[driverclass.type] = driverclass

def datetime2isodate(adatetime=None):
    if not adatetime:
        adatetime = datetime.datetime.now()
    assert(isinstance(adatetime,datetime.datetime))
    return adatetime.isoformat()

def isodate2datetime(isodatestr):
    # we remove the microseconds part as it is not working for python2.5 strptime
    return datetime.datetime.strptime(isodatestr.split('.')[0] , "%Y-%m-%dT%H:%M:%S")

def time2display(adatetime):
    return adatetime.strftime("%Y-%m-%d %H:%M")

def hours_minutes(hours):
    if hours is None:
        return None
    else:
        return "%02i:%02i" % ( int(hours) , int((hours - int(hours)) * 60.0))

def fileisodate(filename):
    return datetime.datetime.fromtimestamp(os.stat(filename).st_mtime).isoformat()

def dateof(adatetime):
    return adatetime.replace(hour=0,minute=0,second=0,microsecond=0)

#####################################
# http://code.activestate.com/recipes/498181-add-thousands-separator-commas-to-formatted-number/
# Code from Michael Robellard's comment made 28 Feb 2010
# Modified for leading +, -, space on 1 Mar 2010 by Glenn Linderman
# 
# Tail recursion removed and  leading garbage handled on March 12 2010, Alessandro Forghieri
def splitThousands( s, tSep=',', dSep='.'):
    '''Splits a general float on thousands. GIGO on general input'''
    if s == None:
        return 0
    if not isinstance( s, str ):
        s = str( s )

    cnt=0
    numChars=dSep+'0123456789'
    ls=len(s)
    while cnt < ls and s[cnt] not in numChars: cnt += 1

    lhs = s[ 0:cnt ]
    s = s[ cnt: ]
    if dSep == '':
        cnt = -1
    else:
        cnt = s.rfind( dSep )
    if cnt > 0:
        rhs = dSep + s[ cnt+1: ]
        s = s[ :cnt ]
    else:
        rhs = ''

    splt=''
    while s != '':
        splt= s[ -3: ] + tSep + splt
        s = s[ :-3 ]

    return lhs + splt[ :-1 ] + rhs


def call_external_process(shell_string):
    p = subprocess.call(shell_string, shell=True)
    if (p != 0 ):
        raise Exception('shell program exited with error code ' + str(p), shell_string)

def check_string(test_string):
    pattern = r'[^\.A-Za-z0-9\-_]'
    if re.search(pattern, test_string):
        #Character other then . a-z 0-9 was found
        print 'Invalid : %r' % (test_string,)

def convert_bytes(bytes):
    if bytes is None:
        return None
    else:        
        bytes = float(bytes)
        if bytes >= 1099511627776:
            terabytes = bytes / 1099511627776
            size = '%.2fT' % terabytes
        elif bytes >= 1073741824:
            gigabytes = bytes / 1073741824
            size = '%.2fG' % gigabytes
        elif bytes >= 1048576:
            megabytes = bytes / 1048576
            size = '%.2fM' % megabytes
        elif bytes >= 1024:
            kilobytes = bytes / 1024
            size = '%.2fK' % kilobytes
        else:
            size = '%.2fb' % bytes
        return size    

## {{{ http://code.activestate.com/recipes/81189/ (r2)
def pp(cursor, data=None, rowlens=0, callback=None):
    """
    pretty print a query result as a table
    callback is a function called for each field (fieldname,value) to format the output
    """
    def defaultcb(fieldname,value):
        return value

    if not callback:
        callback = defaultcb

    d = cursor.description
    if not d:
        return "#### NO RESULTS ###"
    names = []
    lengths = []
    rules = []
    if not data:
        data = cursor.fetchall()
    for dd in d:    # iterate over description
        l = dd[1]
        if not l:
            l = 12             # or default arg ...
        l = max(l, len(dd[0])) # handle long names
        names.append(dd[0])
        lengths.append(l)
    for col in range(len(lengths)):
        if rowlens:
            rls = [len(str(callback(d[col][0],row[col]))) for row in data if row[col]]
            lengths[col] = max([lengths[col]]+rls)
        rules.append("-"*lengths[col])
    format = " ".join(["%%-%ss" % l for l in lengths])
    result = [format % tuple(names)]
    result.append(format % tuple(rules))
    for row in data:
        row_cb=[]
        for col in range(len(d)):
            row_cb.append(callback(d[col][0],row[col]))
        result.append(format % tuple(row_cb))
    return "\n".join(result)
## end of http://code.activestate.com/recipes/81189/ }}}


def html_table(cur,callback=None):
    """
        cur est un cursor issu d'une requete
        callback est une fonction qui prend (rowmap,fieldname,value)
        et renvoie une representation texte
    """
    def safe_unicode(iso):
        if iso is None:
            return None
        elif isinstance(iso, str):
            return iso.decode('iso8859')
        else:
            return iso

    def itermap(cur):
        for row in cur:
            yield dict((cur.description[idx][0], value)
                       for idx, value in enumerate(row))

    head=u"<tr>"+"".join(["<th>"+c[0]+"</th>" for c in cur.description])+"</tr>"
    lines=""
    if callback:
        for r in itermap(cur):
            lines=lines+"<tr>"+"".join(["<td>"+str(callback(r,c[0],safe_unicode(r[c[0]])))+"</td>" for c in cur.description])+"</tr>"
    else:
        for r in cur:
            lines=lines+"<tr>"+"".join(["<td>"+safe_unicode(c)+"</td>" for c in r])+"</tr>"

    return "<table border=1  cellpadding=2 cellspacing=0>%s%s</table>" % (head,lines)


    
def monitor_stdout(aprocess, onoutputdata,context):
    """Reads data from stdout and stderr from aprocess and return as a string
       on each chunk, call a call back onoutputdata(dataread)
    """
    assert(isinstance(aprocess,subprocess.Popen))
    read_set = []
    stdout = []
    line = ''

    if aprocess.stdout:
        read_set.append(aprocess.stdout)
    if aprocess.stderr:
        read_set.append(aprocess.stderr)

    while read_set:
        try:
            rlist, wlist, xlist = select.select(read_set, [], [])
        except select.error, e:
            if e.args[0] == errno.EINTR:
                continue
            raise

        # Reads one line from stdout
        if aprocess.stdout in rlist:
            data = os.read(aprocess.stdout.fileno(), 1)
            if data == "":
                aprocess.stdout.close()
                read_set.remove(aprocess.stdout)
            while data and not data in ('\n','\r'):
                line += data
                data = os.read(aprocess.stdout.fileno(), 1)
            if line or data in ('\n','\r'):
                stdout.append(line)
                if onoutputdata:
                    onoutputdata(line,context)
            line=''

        # Reads one line from stderr
        if aprocess.stderr in rlist:
            data = os.read(aprocess.stderr.fileno(), 1)
            if data == "":
                aprocess.stderr.close()
                read_set.remove(aprocess.stderr)
            while data and not data in ('\n','\r'):
                line += data
                data = os.read(aprocess.stderr.fileno(), 1)
            if line or data in ('\n','\r'):
                stdout.append(line)
                if onoutputdata:
                    onoutputdata(line,context)
            line=''

    aprocess.wait()
    if line:
        stdout.append(line)
        if onoutputdata:
            onoutputdata(line,context)
    return "\n".join(stdout)


class BackupStat:
    dbpath = ''
    db = None
    logger = logging.getLogger('tisbackup')

    def __init__(self,dbpath):
        self.dbpath = dbpath
        if not os.path.isfile(self.dbpath):
            self.db=sqlite3.connect(self.dbpath)
            self.initdb()
        else:
            self.db=sqlite3.connect(self.dbpath) 
            if not "'TYPE'" in str(self.db.execute("select * from stats").description):
                self.updatedb()
                 

    def updatedb(self):
        self.logger.debug('Update stat database')
        self.db.execute("alter table stats add column TYPE TEXT;")
        self.db.execute("update stats set TYPE='BACKUP';")
        self.db.commit()
        
    def initdb(self):
        assert(isinstance(self.db,sqlite3.Connection))
        self.logger.debug('Initialize stat database')
        self.db.execute("""
create table stats (
  backup_name TEXT,
  server_name TEXT,
  description TEXT,
  backup_start TEXT,
  backup_end TEXT,
  backup_duration NUMERIC,
  total_files_count INT,
  written_files_count INT,
  total_bytes INT,
  written_bytes INT,
  status TEXT,
  log TEXT,
  backup_location TEXT,
  TYPE TEXT)""")
        self.db.execute("""
create index idx_stats_backup_name on stats(backup_name);""")
        self.db.execute("""
create index idx_stats_backup_location on stats(backup_location);""")
        self.db.commit()

    def start(self,backup_name,server_name,TYPE,description='',backup_location=None):
        """ Add in stat DB a record for the newly running backup"""
        return self.add(backup_name=backup_name,server_name=server_name,description=description,backup_start=datetime2isodate(),status='Running',TYPE=TYPE)

    def finish(self,rowid,total_files_count=None,written_files_count=None,total_bytes=None,written_bytes=None,log=None,status='OK',backup_end=None,backup_duration=None,backup_location=None):
        """ Update record in stat DB for the finished backup"""
        if not backup_end:
            backup_end = datetime2isodate()
        if backup_duration == None:
            try:
                # get duration using start of backup datetime
                backup_duration = (isodate2datetime(backup_end) - isodate2datetime(self.query('select backup_start from stats where rowid=?',(rowid,))[0]['backup_start'])).seconds / 3600.0
            except:
                backup_duration = None

        # update stat record
        self.db.execute("""\
      update stats set 
        total_files_count=?,written_files_count=?,total_bytes=?,written_bytes=?,log=?,status=?,backup_end=?,backup_duration=?,backup_location=?
      where
        rowid = ?
    """,(total_files_count,written_files_count,total_bytes,written_bytes,log,status,backup_end,backup_duration,backup_location,rowid))
        self.db.commit()

    def add(self,
            backup_name='',
            server_name='',
            description='',
            backup_start=None,
            backup_end=None,
            backup_duration=None,
            total_files_count=None,
            written_files_count=None,
            total_bytes=None,
            written_bytes=None,
            status='draft',
            log='',
            TYPE='',
            backup_location=None):
        if not backup_start:
            backup_start=datetime2isodate()
        if not backup_end:
            backup_end=datetime2isodate()
        
        cur = self.db.execute("""\
      insert into stats (
          backup_name,
          server_name,
          description,
          backup_start,
          backup_end,
          backup_duration,
          total_files_count,
          written_files_count,
          total_bytes,
          written_bytes,
          status,
          log,
          backup_location,
          TYPE) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """,(
           backup_name,
           server_name,
           description,
           backup_start,
           backup_end,
           backup_duration,
           total_files_count,
           written_files_count,
           total_bytes,
           written_bytes,
           status,
           log,
           backup_location,
           TYPE)       
       )

        self.db.commit()
        return cur.lastrowid

    def query(self,query, args=(), one=False):
        """
        execute la requete query sur la db et renvoie un tableau de dictionnaires
        """
        cur = self.db.execute(query, args)
        rv = [dict((cur.description[idx][0], value)
                   for idx, value in enumerate(row)) for row in cur.fetchall()]
        return (rv[0] if rv else None) if one else rv

    def last_backups(self,backup_name,count=30):
        if backup_name:
            cur = self.db.execute('select  * from stats where backup_name=? order by backup_end desc limit ?',(backup_name,count))
        else:
            cur = self.db.execute('select  * from stats order by backup_end desc limit ?',(count,))

        def fcb(fieldname,value):
            if fieldname in ('backup_start','backup_end'):
                return time2display(isodate2datetime(value))
            elif 'bytes' in fieldname:
                return convert_bytes(value)
            elif 'count' in fieldname:
                return splitThousands(value,' ','.')
            elif 'backup_duration' in fieldname:
                return hours_minutes(value)
            else:
                return value

        #for r in self.query('select  * from stats where backup_name=? order by backup_end desc limit ?',(backup_name,count)):
        print pp(cur,None,1,fcb)


    def fcb(self,fields,fieldname,value):
        if fieldname in ('backup_start','backup_end'):
            return time2display(isodate2datetime(value))
        elif 'bytes' in fieldname:
            return convert_bytes(value)
        elif 'count' in fieldname:
            return splitThousands(value,' ','.')
        elif 'backup_duration' in fieldname:
            return hours_minutes(value)
        else:
            return value

    def as_html(self,cur):
        if cur:
            return html_table(cur,self.fcb)
        else:
            return html_table(self.db.execute('select * from stats order by backup_start asc'),self.fcb)


def ssh_exec(command,ssh=None,server_name='',remote_user='',private_key='',ssh_port=22):
    """execute command on server_name using the provided ssh connection 
      or creates a new connection if ssh is not provided.
      returns (exit_code,output)

      output is the concatenation of stdout and stderr
    """
    if not ssh:
        assert(server_name and remote_user and private_key)
        try:
            mykey = paramiko.RSAKey.from_private_key_file(private_key)
        except paramiko.SSHException:
            mykey = paramiko.DSSKey.from_private_key_file(private_key)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(server_name,username=remote_user,pkey = private_key,port=ssh_port)

    tran = ssh.get_transport()
    chan = tran.open_session()

    # chan.set_combine_stderr(True)
    chan.get_pty()
    stdout = chan.makefile()

    chan.exec_command(command)
    stdout.flush()
    output = stdout.read()
    exit_code = chan.recv_exit_status()
    return (exit_code,output)


class backup_generic:
    """Generic ancestor class for backups, not registered"""
    type = 'generic'
    required_params = ['type','backup_name','backup_dir','server_name','backup_retention_time','maximum_backup_age']
    optional_params = ['preexec','postexec','description','private_key','remote_user','ssh_port']

    logger = logging.getLogger('tisbackup')
    backup_name = ''
    backup_dir = ''
    server_name = ''
    remote_user = 'root'
    description = ''
    dbstat = None
    dry_run = False
    preexec = ''
    postexec = ''
    maximum_backup_age = None
    backup_retention_time = None
    verbose = False
    private_key=''
    ssh_port=22

    def __init__(self,backup_name, backup_dir,dbstat=None,dry_run=False):
        if not re.match('^[A-Za-z0-9_\-\.]*$',backup_name):
            raise Exception('The backup name %s should contain only alphanumerical characters' % backup_name) 
        self.backup_name = backup_name
        self.backup_dir = backup_dir

        self.dbstat = dbstat
        assert(isinstance(self.dbstat,BackupStat) or self.dbstat==None)

        if not os.path.isdir(self.backup_dir):
            os.makedirs(self.backup_dir)

        self.dry_run = dry_run

    @classmethod
    def get_help(cls):
        return """\
%(type)s : %(desc)s
  Required params : %(required)s
  Optional params : %(optional)s
""" % {'type':cls.type,
       'desc':cls.__doc__,
       'required':",".join(cls.required_params),
       'optional':",".join(cls.optional_params)}

    def check_required_params(self):
        for name in self.required_params:
            if not hasattr(self,name) or not getattr(self,name):
                raise Exception('[%s] Config Attribute %s is required' % (self.backup_name,name))
        if (self.preexec or self.postexec) and (not self.private_key or not self.remote_user):
            raise Exception('[%s] remote_user and private_key file required if preexec or postexec is used' % self.backup_name)


    def read_config(self,iniconf):
        assert(isinstance(iniconf,ConfigParser))
        allowed_params = self.required_params+self.optional_params
        for (name,value) in iniconf.items(self.backup_name):
            if not name in allowed_params:
                self.logger.critical('[%s] Invalid param name "%s"', self.backup_name,name);
                raise Exception('[%s] Invalid param name "%s"', self.backup_name,name)
            self.logger.debug('[%s] reading param %s = %s ', self.backup_name,name,value)
            setattr(self,name,value)

        # if retention (in days) is not defined at section level, get default global one.
        if not self.backup_retention_time:
            self.backup_retention_time = iniconf.getint('global','backup_retention_time')    

        # for nagios, if maximum last backup age (in hours) is not defined at section level, get default global one.
        if not self.maximum_backup_age:
            self.maximum_backup_age = iniconf.getint('global','maximum_backup_age')

        self.ssh_port = int(self.ssh_port)
        self.backup_retention_time = int(self.backup_retention_time)
        self.maximum_backup_age = int(self.maximum_backup_age)

        self.check_required_params()


    def do_preexec(self,stats):
        self.logger.info("[%s] executing preexec %s ",self.backup_name,self.preexec)
        try:
            mykey = paramiko.RSAKey.from_private_key_file(self.private_key)
        except paramiko.SSHException:
            mykey = paramiko.DSSKey.from_private_key_file(self.private_key)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.server_name,username=self.remote_user,pkey = mykey)
        tran = ssh.get_transport()
        chan = tran.open_session()

        # chan.set_combine_stderr(True)
        chan.get_pty()
        stdout = chan.makefile()

        if not self.dry_run:
            chan.exec_command(self.preexec)
            output = stdout.read()
            exit_code = chan.recv_exit_status()
            self.logger.info('[%s] preexec exit code : "%i", output : %s',self.backup_name , exit_code, output )
            return exit_code
        else:
            return 0

    def do_postexec(self,stats):
        self.logger.info("[%s] executing postexec %s ",self.backup_name,self.postexec)
        try:
            mykey = paramiko.RSAKey.from_private_key_file(self.private_key)
        except paramiko.SSHException:
            mykey = paramiko.DSSKey.from_private_key_file(self.private_key)

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(self.server_name,username=self.remote_user,pkey = mykey)
        tran = ssh.get_transport()
        chan = tran.open_session()

        # chan.set_combine_stderr(True)
        chan.get_pty()
        stdout = chan.makefile()

        if not self.dry_run:
            chan.exec_command(self.postexec)
            output = stdout.read()
            exit_code = chan.recv_exit_status()
            self.logger.info('[%s] postexec exit code : "%i", output : %s',self.backup_name , exit_code, output )
            return exit_code
        else:
            return 0


    def do_backup(self,stats):
        """stats dict with keys : total_files_count,written_files_count,total_bytes,written_bytes"""
        pass

    def check_params_connections(self):
        """Perform a dry run trying to connect without actually doing backup"""
        self.check_required_params()

    def process_backup(self):
        """Process the backup.
          launch 
           - do_preexec
           - do_backup
           - do_postexec

          returns a dict for stats
        """
        self.logger.info('[%s] ######### Starting backup',self.backup_name)

        starttime = time.time()
        self.backup_start_date = datetime.datetime.now().strftime('%Y%m%d-%Hh%Mm%S')

        if not self.dry_run and self.dbstat:
            stat_rowid = self.dbstat.start(backup_name=self.backup_name,server_name=self.server_name,TYPE="BACKUP")
        else:
            stat_rowid = None

        try:
            stats = {}
            stats['total_files_count']=0
            stats['written_files_count']=0
            stats['total_bytes']=0
            stats['written_bytes']=0
            stats['log']=''
            stats['status']='Running'
            stats['backup_location']=None

            if self.preexec.strip():
                exit_code = self.do_preexec(stats)
                if exit_code != 0 :
                    raise Exception('Preexec "%s" failed with exit code "%i"' % (self.preexec,exit_code))

            self.do_backup(stats)

            if self.postexec.strip():
                exit_code = self.do_postexec(stats)
                if exit_code != 0 :
                    raise Exception('Postexec "%s" failed with exit code "%i"' % (self.postexec,exit_code))

            endtime = time.time()
            duration = (endtime-starttime)/3600.0
            if not self.dry_run and self.dbstat:
                self.dbstat.finish(stat_rowid,
                                   backup_end=datetime2isodate(datetime.datetime.now()),
                                   backup_duration = duration,
                                   total_files_count=stats['total_files_count'],
                                   written_files_count=stats['written_files_count'],
                                   total_bytes=stats['total_bytes'],
                                   written_bytes=stats['written_bytes'],
                                   status=stats['status'],
                                   log=stats['log'],
                                   backup_location=stats['backup_location'])

            self.logger.info('[%s] ######### Backup finished : %s',self.backup_name,stats['log'])
            return stats

        except BaseException, e:
            stats['status']='ERROR'
            stats['log']=str(e)
            endtime = time.time()
            duration = (endtime-starttime)/3600.0
            if not self.dry_run and self.dbstat:
                self.dbstat.finish(stat_rowid,
                                   backup_end=datetime2isodate(datetime.datetime.now()),
                                   backup_duration = duration,
                                   total_files_count=stats['total_files_count'],
                                   written_files_count=stats['written_files_count'],
                                   total_bytes=stats['total_bytes'],
                                   written_bytes=stats['written_bytes'],
                                   status=stats['status'],
                                   log=stats['log'],
                                   backup_location=stats['backup_location'])

            self.logger.error('[%s] ######### Backup finished with ERROR: %s',self.backup_name,stats['log'])
            raise     


    def checknagios(self,maxage_hours=30):
        """
        Returns a tuple (nagiosstatus,message) for the current backup_name
        Read status from dbstat database
        """
        if not self.dbstat:
            self.logger.warn('[%s] checknagios : no database provided',self.backup_name)
            return ('No database provided',nagiosStateUnknown)
        else:
            self.logger.debug('[%s] checknagios : sql query "%s" %s',self.backup_name,'select status, backup_end, log from stats where TYPE=\'BACKUP\' AND backup_name=? order by backup_end desc limit 30',self.backup_name)
            q = self.dbstat.query('select status, backup_start, backup_end, log, backup_location, total_bytes from stats where TYPE=\'BACKUP\' AND backup_name=? order by backup_start desc limit 30',(self.backup_name,))
            if not q:
                self.logger.debug('[%s] checknagios : no result from query',self.backup_name)
                return (nagiosStateCritical,'CRITICAL : No backup found for %s in database' % self.backup_name)
            else:
                mindate = datetime2isodate((datetime.datetime.now() - datetime.timedelta(hours=maxage_hours)))
                self.logger.debug('[%s] checknagios : looking for most recent OK not older than %s',self.backup_name,mindate)
                for b in q:
                    if b['backup_end'] >= mindate and b['status'] == 'OK':
                        # check if backup actually exists on registered backup location and is newer than backup start date
                        if b['total_bytes'] == 0:
                            return (nagiosStateWarning,"WARNING : No data to backup was found for %s" % (self.backup_name,))

                        if not b['backup_location']:
                            return (nagiosStateWarning,"WARNING : No Backup location found for %s finished on (%s) %s" % (self.backup_name,isodate2datetime(b['backup_end']),b['log']))

                        if os.path.isfile(b['backup_location']):
                            backup_actual_date = datetime.datetime.fromtimestamp(os.stat(b['backup_location']).st_ctime)
                            if backup_actual_date + datetime.timedelta(hours = 1) > isodate2datetime(b['backup_start']):
                                return (nagiosStateOk,"OK Backup %s (%s), %s" % (self.backup_name,isodate2datetime(b['backup_end']),b['log']))
                            else:
                                return (nagiosStateCritical,"CRITICAL Backup %s (%s), %s seems older than start of backup" % (self.backup_name,isodate2datetime(b['backup_end']),b['log']))
                        elif os.path.isdir(b['backup_location']):
                            return (nagiosStateOk,"OK Backup %s (%s), %s" % (self.backup_name,isodate2datetime(b['backup_end']),b['log']))
                        else:
                            return (nagiosStateCritical,"CRITICAL Backup %s (%s), %s has disapeared from backup location %s" % (self.backup_name,isodate2datetime(b['backup_end']),b['log'],b['backup_location']))

                self.logger.debug('[%s] checknagios : looking for most recent Warning or Running not older than %s',self.backup_name,mindate)
                for b in q:
                    if b['backup_end'] >= mindate and b['status'] in ('Warning','Running'):
                        return (nagiosStateWarning,'WARNING : Backup %s still running or warning. %s' % (self.backup_name,b['log']))

                self.logger.debug('[%s] checknagios : No Ok or warning recent backup found',self.backup_name)
                return (nagiosStateCritical,'CRITICAL : No recent backup for %s' % self.backup_name )

    def cleanup_backup(self):
        """Removes obsolete backups (older than backup_retention_time)"""
        mindate = datetime2isodate((dateof(datetime.datetime.now()) - datetime.timedelta(days=self.backup_retention_time)))
        # check if there is at least 1 "OK" backup left after cleanup :
        ok_backups = self.dbstat.query('select backup_location from stats where TYPE="BACKUP" and backup_name=? and backup_start>=? and status="OK" order by backup_start desc',(self.backup_name,mindate))
        removed = []
        if ok_backups and os.path.exists(ok_backups[0]['backup_location']):
            records = self.dbstat.query('select status, backup_start, backup_end, log, backup_location from stats where backup_name=? and backup_start<? and backup_location is not null and TYPE="BACKUP" order by backup_start',(self.backup_name,mindate))
            if records:
                for oldbackup_location in [rec['backup_location'] for rec in records if rec['backup_location']]:
                    try:
                        if os.path.isdir(oldbackup_location) and self.backup_dir in oldbackup_location :
                            self.logger.info('[%s] removing directory "%s"',self.backup_name,oldbackup_location)
                            if not self.dry_run:
                                shutil.rmtree(oldbackup_location.encode('ascii'))
                        if os.path.isfile(oldbackup_location) and self.backup_dir in oldbackup_location :
                            self.logger.debug('[%s] removing file "%s"',self.backup_name,oldbackup_location)
                            if not self.dry_run:
                                os.remove(oldbackup_location)             
                        self.logger.debug('Cleanup_backup : Removing records from DB : [%s]-"%s"',self.backup_name,oldbackup_location)
                        if not self.dry_run:
                            self.dbstat.db.execute('update stats set TYPE="CLEAN" where backup_name=? and backup_location=?',(self.backup_name,oldbackup_location))
                            self.dbstat.db.commit()
                    except BaseException,e:
                        self.logger.error('cleanup_backup : Unable to remove directory/file "%s". Error %s', oldbackup_location,e)
                    removed.append((self.backup_name,oldbackup_location))
            else:
                self.logger.debug('[%s] cleanup : no result for query',self.backup_name)
        else:
            self.logger.info('Nothing to do because we want to keep at least one OK backup after cleaning')

        self.logger.info('[%s] Cleanup finished : removed : %s' , self.backup_name,','.join([('[%s]-"%s"') % r for r in removed]) or 'Nothing')
        return removed

    def register_existingbackups(self):
        """scan existing backups and insert stats in database"""
        registered = [b['backup_location'] for b in self.dbstat.query('select distinct backup_location from stats where backup_name=?',self.backup_name)]
        raise Exception('Abstract method')
    
    def export_latestbackup(self,destdir):
        """Copy (rsync) latest OK backup to external storage located at locally mounted "destdir"
        """
        stats = {}
        stats['total_files_count']=0
        stats['written_files_count']=0
        stats['total_bytes']=0
        stats['written_bytes']=0
        stats['log']=''
        stats['status']='Running'
        if not self.dbstat:
            self.logger.critical('[%s] export_latestbackup : no database provided',self.backup_name)
            raise Exception('No database')
        else:
            latest_sql = """\
              select status, backup_start, backup_end, log, backup_location, total_bytes 
              from stats 
              where backup_name=? and status='OK' and TYPE='BACKUP'
              order by backup_start desc limit 30"""
            self.logger.debug('[%s] export_latestbackup : sql query "%s" %s',self.backup_name,latest_sql,self.backup_name) 
            q = self.dbstat.query(latest_sql,(self.backup_name,))
            if not q:
                self.logger.debug('[%s] export_latestbackup : no result from query',self.backup_name)
                raise Exception('No OK backup found for %s in database' % self.backup_name)
            else:
                latest = q[0]
                backup_source = latest['backup_location']
                backup_dest = os.path.join(os.path.abspath(destdir),self.backup_name)
                if not os.path.exists(backup_source):
                    raise Exception('Backup source %s doesn\'t exists' % backup_source)

                # ensure there is a slash at end
                if os.path.isdir(backup_source) and backup_source[-1] <> '/':
                    backup_source += '/'
                    if backup_dest[-1] <> '/':
                        backup_dest += '/'
                
                if not os.path.isdir(backup_dest):
                    os.makedirs(backup_dest)
                    
                options = ['-aP','--stats','--delete-excluded','--numeric-ids','--delete-after']
                if self.logger.level:
                    options.append('-P')

                if self.dry_run:
                    options.append('-d')

                options_params = " ".join(options)

                cmd = '/usr/bin/rsync %s %s %s 2>&1' % (options_params,backup_source,backup_dest)
                self.logger.debug("[%s] rsync : %s",self.backup_name,cmd)

                if not self.dry_run:
                    self.line = ''
                    starttime = time.time()
                    stat_rowid = self.dbstat.start(backup_name=self.backup_name,server_name=self.server_name, TYPE="EXPORT")

                    process = subprocess.Popen(cmd, shell=True,  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, close_fds=True)
                    def ondata(data,context):
                        if context.verbose:
                            print data
                        context.logger.debug(data)

                    log = monitor_stdout(process,ondata,self)

                    for l in log.splitlines():
                        if l.startswith('Number of files:'):
                            stats['total_files_count'] += int(l.split(':')[1])
                        if l.startswith('Number of files transferred:'):
                            stats['written_files_count'] += int(l.split(':')[1])
                        if l.startswith('Total file size:'):
                            stats['total_bytes'] += int(l.split(':')[1].split()[0])
                        if l.startswith('Total transferred file size:'):
                            stats['written_bytes'] += int(l.split(':')[1].split()[0])
                    returncode = process.returncode
                    ## deal with exit code 24 (file vanished)
                    if (returncode == 24):
                        self.logger.warning("[" + self.backup_name + "] Note: some files vanished before transfer")
                    elif (returncode == 23):
                        self.logger.warning("[" + self.backup_name + "] unable so set uid on some files")
                    elif (returncode != 0):
                        self.logger.error("[" + self.backup_name + "] shell program exited with error code ")
                        raise Exception("[" + self.backup_name + "] shell program exited with error code " + str(returncode), cmd)
                else:
                    print cmd

                stats['status']='OK'
                self.logger.info('export backup from %s to %s OK, %d bytes written for %d changed files' % (backup_source,backup_dest,stats['written_bytes'],stats['written_files_count']))
                
                endtime = time.time()
                duration = (endtime-starttime)/3600.0

                if not self.dry_run and self.dbstat:
                    self.dbstat.finish(stat_rowid,
                                       backup_end=datetime2isodate(datetime.datetime.now()),
                                       backup_duration = duration,
                                       total_files_count=stats['total_files_count'],
                                       written_files_count=stats['written_files_count'],
                                       total_bytes=stats['total_bytes'],
                                       written_bytes=stats['written_bytes'],
                                       status=stats['status'],
                                       log=stats['log'],
                                       backup_location=backup_dest)
                return stats


if __name__ == '__main__':
    logger = logging.getLogger('tisbackup')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    dbstat = BackupStat('/backup/data/log/tisbackup.sqlite') 
