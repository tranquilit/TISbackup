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
from common import *
import XenAPI
import time
import logging
import re
import os.path
import datetime
import select
import urllib2, urllib
import base64
import socket
import requests
import pexpect
from stat import *


class backup_switch(backup_generic):
    """Backup a startup-config on a switch"""
    type = 'switch'

    required_params = backup_generic.required_params + ['switch_ip','switch_type']
    optional_params = backup_generic.optional_params + [ 'switch_user', 'switch_password']

    switch_user = ''
    switch_password = ''

    def switch_hp(self, filename):

        s = socket.socket()
        try:
            s.connect((self.switch_ip, 23))
            s.close()
        except:
            raise

        child=pexpect.spawn('telnet '+self.switch_ip)
        time.sleep(1)
        if self.switch_user != "":
            child.sendline(self.switch_user)
            child.sendline(self.switch_password+'\r')
        else:
            child.sendline(self.switch_password+'\r')
        try:
            child.expect("#")
        except:
            raise Exception("Bad Credentials")
        child.sendline( "terminal length 1000\r")
        child.expect("#")
        child.sendline( "show config\r")
        child.maxread = 100000000
        child.expect("Startup.+$")
        lines = child.after
        if "-- MORE --" in  lines:
            raise Exception("Terminal lenght is not sufficient")
        child.expect("#")
        lines += child.before
        child.sendline("logout\r")
        child.send('y\r')
        for line in lines.split("\n")[1:-1]:
            open(filename,"a").write(line.strip()+"\n")

    def switch_cisco(self, filename):
        s = socket.socket()
        try:
            s.connect((self.switch_ip, 23))
            s.close()
        except:
            raise

        child=pexpect.spawn('telnet '+self.switch_ip)
        time.sleep(1)
        if self.switch_user:
            child.sendline(self.switch_user)
        child.expect('Password: ')
        child.sendline(self.switch_password+'\r')
        try:
            child.expect(">")
        except:
            raise Exception("Bad Credentials")
        child.sendline('enable\r')
        child.expect('Password: ')
        child.sendline(self.switch_password+'\r')
        try:
            child.expect("#")
        except:
            raise Exception("Bad Credentials")
        child.sendline( "terminal length 0\r")
        child.expect("#")
        child.sendline("show run\r")
        child.expect('Building configuration...')
        child.expect("#")
        running_config = child.before
        child.sendline("show vlan\r")
        child.expect('VLAN')
        child.expect("#")
        vlan = 'VLAN'+child.before
        open(filename,"a").write(running_config+'\n'+vlan)
        child.send('exit\r')
        child.close()


    def switch_linksys_SRW2024(self, filename):
        s = socket.socket()
        try:
            s.connect((self.switch_ip, 23))
            s.close()
        except:
            raise

        child=pexpect.spawn('telnet '+self.switch_ip)
        time.sleep(1)
        if hasattr(self,'switch_password'):
            child.sendline(self.switch_user+'\t')
            child.sendline(self.switch_password+'\r')
        else:
            child.sendline(self.switch_user+'\r')
        try:
            child.expect('Menu')
        except:
            raise Exception("Bad Credentials")
        child.sendline('\032')
        child.expect('>')
        child.sendline('lcli')
        child.expect("Name:")
        if hasattr(self,'switch_password'):
            child.send(self.switch_user+'\r'+self.switch_password+'\r')
        else:
            child.sendline(self.switch_user)
        child.expect(".*#")
	child.sendline( "terminal datadump")
	child.expect("#")
        child.sendline( "show startup-config")
        child.expect("#")
        lines = child.before
        if "Unrecognized command" in lines:
            raise Exception("Bad Credentials")
        child.sendline("exit")
        #child.expect( ">")
        #child.sendline("logout")
        for line in lines.split("\n")[1:-1]:
            open(filename,"a").write(line.strip()+"\n")


    def switch_dlink_DGS1210(self, filename):
        login_data = {'Login' : self.switch_user, 'Password' : self.switch_password, 'sellanId' : 0, 'sellan' : 0, 'lang_seqid' : 1}
        resp = requests.post('http://%s/form/formLoginApply' % self.switch_ip, data=login_data, headers={"Referer":'http://%s/www/login.html' % self.switch_ip})
        if "Wrong password" in resp.text:
            raise Exception("Wrong password")
        resp = requests.post("http://%s/BinFile/config.bin" % self.switch_ip, headers={"Referer":'http://%s/www/iss/013_download_cfg.html' % self.switch_ip})
        with  open(filename, 'w') as f:
            f.write(resp.content)

    def switch_dlink_DGS1510(self, filename):
        s = socket.socket()
        try:
            s.connect((self.switch_ip, 23))
            s.close()
        except:
            raise

        child = pexpect.spawn('telnet ' + self.switch_ip)
        time.sleep(1)
        if self.switch_user:
            child.sendline(self.switch_user)
        child.expect('Password:')
        child.sendline(self.switch_password + '\r')
        try:
            child.expect("#")
        except:
            raise Exception("Bad Credentials")
        child.sendline("terminal length 0\r")
        child.expect("#")
        child.sendline("show run\r")
        child.logfile_read = open(filename, "a")
        child.expect('End of configuration file')
        child.expect('#--')
        child.expect("#")
        child.close()
        myre = re.compile("#--+")
        config = myre.split(open(filename).read())[2]
        with open(filename,'w') as f:
            f.write(config)


    def do_backup(self,stats):
        try:
            dest_filename = os.path.join(self.backup_dir,"%s-%s" % (self.backup_name,self.backup_start_date))

            options = []
            options_params = " ".join(options)
            if "LINKSYS-SRW2024" == self.switch_type:
                dest_filename += '.txt'
                self.switch_linksys_SRW2024(dest_filename)
            elif self.switch_type in [ "CISCO", ]:
                dest_filename += '.txt'
                self.switch_cisco(dest_filename)
            elif self.switch_type in [ "HP-PROCURVE-4104GL", "HP-PROCURVE-2524" ]:
                dest_filename += '.txt'
                self.switch_hp(dest_filename)
            elif "DLINK-DGS1210" == self.switch_type:
                dest_filename += '.bin'
                self.switch_dlink_DGS1210(dest_filename)
            elif "DLINK-DGS1510" == self.switch_type:
                dest_filename += '.cfg'
                self.switch_dlink_DGS1510(dest_filename)
            else:
                raise Exception("Unknown Switch type")

            stats['total_files_count']=1
            stats['written_files_count']=1
            stats['total_bytes']= os.stat(dest_filename).st_size
            stats['written_bytes'] = stats['total_bytes']
            stats['backup_location'] = dest_filename
            stats['status']='OK'
            stats['log']='Switch backup from %s OK, %d bytes written' % (self.server_name,stats['written_bytes'])


        except BaseException , e:
            stats['status']='ERROR'
            stats['log']=str(e)
            raise



register_driver(backup_switch)

if __name__=='__main__':
    logger = logging.getLogger('tisbackup')
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    cp = ConfigParser()
    cp.read('/opt/tisbackup/configtest.ini')
    b = backup_xva()
    b.read_config(cp)

