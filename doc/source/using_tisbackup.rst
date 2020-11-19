.. Reminder for header structure:
  Level 1: ====================
  Level 2: --------------------
  Level 3: ++++++++++++++++++++
  Level 4: """"""""""""""""""""
  Level 5: ^^^^^^^^^^^^^^^^^^^^

.. meta::
  :description: Using TISBackup
  :keywords: Documentation, TISBackup, usage, options, exporting

.. |clap| image:: wapt-resources/clapping-hands-microsoft.png
  :scale: 50%
  :alt: Clapping hands

Using TISBackup
===============

.. _using_tisbackup:

As seen in the :ref:`section on installing TISbackup<install_tisbackup_debian>`,
once the TISBackup installation is up and running,
we have the choice of these actions:

.. code-block:: ini

  backup: launch all backups or a specific one if -s option is used
  cleanup: removed backups older than retension period
  checknagios: check all or a specific backup against max_backup_age parameter
  dumpstat: dump the content of database for the last 20 backups
  retryfailed:  try to relaunch the last failed backups
  listdrivers:  list available backup types and parameters for config inifile
  exportbackup:  copy lastest OK backups from local to location defned by --exportdir parameter
  register_existing: scan backup directories and add missing backups to database

The 3 following options can be used with any tisbackup action.

* the ``-c`` *config_file* option allows to specify a backup file,
  by default :file:`/etc/tis/tisbackup-config.ini` is used:

  .. code-block:: bash

    tisbackup backup -c /etc/toto/test-config.ini

* the ``-s`` *section_name* option allows to launch only the action
  on the specified section:

  .. code-block:: bash

    tisbackup backup -s section_name

* the ``-d`` option allows you to simulate an action in order
  to see the commands launched by it.

  .. code-block:: bash

    tisbackup backup -d

* :command:`backup` launches a backup action:

  .. code-block:: bash

    tisbackup backup

* :command:`cleanup` removes backups older than the time specified
  in the ``backup_retention_time`` parameter of the configuration file:

  .. code-block:: bash

    tisbackup cleanup

* :command:`checknagios` allows the backup information to be uploaded
  to the nagios monitoring server:

  .. code-block:: bash

    tisbackup checknagios

* :command:`dumpstat` displays all information about the last 20 backups
  in tabular format:

  .. code-block:: bash

    tisbackup dumpstat

* :command:`retryfailed` restarts only the backup of the failed sections:

  .. code-block:: bash

    tisbackup retryfailed

* :command:`listdrivers` lists all the possible types of backups
  and their parameters:

  .. code-block:: bash

    tisbackup listdrivers

* :command:`exportbackup` copies the last good backup
  to a directory, you must use the ``--exportdir`` option to specify
  or copy the export:

  .. code-block:: bash

    tisbackup exportbackup --exportdir example_directory

* :command:`register_existing` checks the backup directory and saves information
  from previous backups to tisbackup in the database;

Exporting backups
-----------------

With this procedure, you will be able to export your backups
on USB Hard Disk Drives for your off-line backup needs.

The partition of your HDD must be **ext4** formated and labeled *tisbackup*.

.. code-block:: bash

  fdisk /dev/xvdc
  Command (m for help): n
  Select (default p): p
  Partition number (1-4, default 1): 1
  "Enter"
  "Enter"
  Command (m for help): w

  mkfs.ext4 /dev/xvdc1
  e2label /dev/xvdc1 tisbackup

.. figure:: wapt-resources/tisbackup_hdd_export.png
  :align: center
  :scale: 100%
  :alt: Exporting a backup to an external USB HDD

  Exporting a backup to an external USB HDD

.. figure:: wapt-resources/tisbackup_hdd_export_status.png
  :align: center
  :scale: 100%
  :alt: Status of exported backups

  Status of exported backups
