from huey import RedisHuey
import os
import logging
from tisbackup import tis_backup

huey = RedisHuey('tisbackup', host='localhost')
@huey.task()
def run_export_backup(base, config_file, mount_point, backup_sections):
    try:
        #Log
        logger = logging.getLogger('tisbackup')
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Main
        logger.info("Running export....")

        if backup_sections:
            backup_sections = backup_sections.split(",")
        else:
            backup_sections = []
        backup = tis_backup(dry_run=False,verbose=True,backup_base_dir=base)
        backup.read_ini_file(config_file)
        mount_point = mount_point
        backup.export_backups(backup_sections,mount_point)
    except Exception as e:
        return(str(e))

    finally:
        os.system("/bin/umount %s" % mount_point)
        os.rmdir(mount_point)
    return "ok"

def get_task():
   return task

def set_task(my_task):
   global task
   task = my_task


task = None
