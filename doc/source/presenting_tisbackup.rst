.. Reminder for header structure:
  Level 1: ====================
  Level 2: --------------------
  Level 3: ++++++++++++++++++++
  Level 4: """"""""""""""""""""
  Level 5: ^^^^^^^^^^^^^^^^^^^^

.. meta::
  :description: Technical background for TISBackup
  :keywords: Documentation, TISBackup, technical background

.. |clap| image:: wapt-resources/clapping-hands-microsoft.png
  :scale: 50%
  :alt: Clapping hands

Technical background for TISBackup
==================================

The deduplication of this solution is based on the hardlinks
of ext3/4 file systems used for storing backup files.

The backup server must run :program:`rsync` in server mode,
and the workstations to be backed up must be equipped with :program:`rsync`
and :program:`ssh` (usually basic on machines running GNU/Linux,
with :program:`cygwin` (or another tool like :program:`cwrsync`)
for machines running MS Windows).

tisbackup
---------

:program:`tisbackup` is a python script that the backup server runs
at regular intervals. The configuration file :file:`tisbackup.ini` contains
the details of the tasks to be executed.

:program:`tisbackup` has different options for its execution,
available in the :command:`tisbackup --help` command,
the main ones being the following:

* :command:`backup`: executes all scheduled backups;

* :command:`cleanup`: examines the backups and deletes those
  that are older than the defined maximum retention time ;

* :command:`checknagios`: returns the content that can be viewed by nagios ;

* :command:`retryfailed`: redoes the backups that previously failed;

* :command:`exportbackup`: exports the last valid backups
  to the specified location (remote, external media, ...);

* :command:`register_existing`: scans the backups that have been made
  and adds the missing ones to the database;

tisbackup.ini
-------------

:file:`tisbackup.ini` defines the backups to be executed and supervised.
It is written with a simple formalism.

The different types of backups are:

* ``rsync``: the backup of a directory by rsync using the rsync protocol;

* ``rsync+ssh``: the backup of a directory by rsync with the ssh protocol;

* ``mysql+ssh``: saving a mysql database in a gzipped sql file,
  with the ssh protocol;

* ``pgsql+ssh``: the backup of a postgresql database in a gzipped sql file,
  with the ssh protocol;

* ``xen-xva``: the backup of a virtual machine running on an XCP server
  as an XVA file;

* ``xen-meta-data``: the backup of XCP metadata from a virtualization server;

* ``switch``: the backup of switches;

* ``null``: null backup of a server that does not require a backup but for which
  it is known to be taken into account (Nagios supervision);

The first part of the :file:`tisbackup.ini` file,
starting with the ``[Global]`` tag, determines:

* the path to the folder where the backups will be stored;

* the maximum retention time of a backup (in days);

* the maximum delay before triggering a nagios critical message (in hours);

* possibly the limit of usable bandwidth;

The rest of the file lists the different backups to be made,
with specific parameters for each type of backup:

* name of the directory in the backup;

* backup type;

* server name;

* directory (in case of a directory backup);

* directories to be excluded (idem);

* location of the ssh key to be used (private key on the backup server);

* name of the database (in case of mysql or postgresql database backup);

* ssh port number to use;

* database user and password (in case of mysql or postgresql database backup);

tisbackup.sql
-------------

:file:`tisbackup.sql` is the :program:`sqlite` database available
on the backup server, in which the backup information of each
of the backed up areas is stored. It is used in particular to gather
the information necessary for Nagios.

TISbackup GUI
-------------

Also developed in python, TISbackup GUI is a graphical interface
that allows you to:

* visualize the last backups;

* export a backup to a USB media;

* visualize the backups to be made;

|clap| You may now go on to the next step
and :ref:`install TISBackup on your Debian<base_debian_server_install>`.
