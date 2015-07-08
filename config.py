import os,sys
from huey.backends.sqlite_backend import SqliteQueue,SqliteDataStore
from huey.api import Huey, create_task


tisbackup_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
tasks_db = os.path.join(tisbackup_root_dir,"tasks.sqlite")
queue = SqliteQueue('tisbackups',tasks_db)
result_store = SqliteDataStore('tisbackups',tasks_db)
huey = Huey(queue,result_store,always_eager=False)
