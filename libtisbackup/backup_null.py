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


class backup_null(backup_generic):
    """Null backup to register servers which don't need any backups 
    but we still want to know they are taken in account"""
    type = 'null'
    
    required_params = ['type','server_name','backup_name']
    optional_params = []

    def do_backup(self,stats):
        pass
    def process_backup(self):
        pass
    def cleanup_backup(self):
        pass
    def register_existingbackups(self):
        pass
    def export_latestbackup(self,destdir):
        return {}
    def checknagios(self,maxage_hours=30):
        return (nagiosStateOk,"No backups needs to be performed")
         
register_driver(backup_null)

if __name__=='__main__':
    pass
    
