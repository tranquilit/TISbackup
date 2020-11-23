.. Reminder for header structure:
  Level 1: ====================
  Level 2: --------------------
  Level 3: ++++++++++++++++++++
  Level 4: """"""""""""""""""""
  Level 5: ^^^^^^^^^^^^^^^^^^^^

.. meta::
  :description: Configuring the backup jobs
  :keywords: Documentation, TISBackup, configuration, backup jobs

.. |clap| image:: tisbackup-resources/clapping-hands-microsoft.png
  :scale: 50%
  :alt: Clapping hands

Configuring the backup jobs
===========================

.. _configuring_backup_jobs:

The configuration of the backups is done in an :mimetype:`.ini` file,
by default :file:`/etc/tis/tisbackup-config.ini`:

* a global section where general parameters are specified;

* then for each backup a section will be created;

[global] section
----------------

Here are the mandatory parameters of the global section.

* the beginning of the global section starts with:

  .. code-block:: ini

    [global]

* specify directory where to store backups:

  .. code-block:: ini

    backup_base_dir = /backup/data/

* define the maximum age of the backups (variable used by the cleanup function):

  .. code-block:: ini

    backup_retention_time=140

* define the maximum time in hours between each backup.
  When this time is exceeded, then :program:`checknagios` goes critical:

  .. code-block:: ini

    maximum_backup_age=30

Another non-mandatory parameter allows to define the rsync compression level:
``compression_level=7``.

Backup types
------------

.. note:: to test with a Windows box

Globally, the backups are done through an SSH connection and the steps are:

* creating the **section** in the configuration file;

* installing ssh on the Linux client;

* making an ssh key exchange between the tisbackup server
  and the client to back up;

Here are the different types of backup possible with :program:`tisbackup`.

Backing up a MySQL database
+++++++++++++++++++++++++++

.. code-block:: ini

  [srvintranet_mysql_mediawiki]
  type=mysql+ssh
  server_name=srvintranet
  private_key=/root/.ssh/id_dsa
  db_name=mediawiki
  db_user=user
  db_passwd=password

Mandatory parameters:

* ``[srvintranet_mysql_mediawiki]``: name of the section starts
  with the name you give to it;

* ``type``: specifies the backup type for the Mysql database dump;

* ``server_name``: defines the server to be backed up
  by its DNS name or IP address;

* ``private_key``: defines the name of the private key to be used
  to connect to the client;

* ``db_name``: defines the name of the database to dump;

* ``db_user``: defines the name of a user with the right to dump on the basis of;

* ``db_passwd``: defines the user's password;

Backing up a PostgreSQL database
++++++++++++++++++++++++++++++++

.. code-block:: ini

  [srvasterisk-pgsql]
  type=pgsql+ssh
  server_name=srvasterisk
  private_key=/root/.ssh/id_rsa
  db_name=asterisk

Mandatory parameters:

* ``[srvasterisk-pgsql]``: name of the section starts
  with the name you give to it;

* ``type``: specifies the backup type for the Mysql database dump;

* ``server_name``: defines the server to be backed up
  by its DNS name or IP address;

* ``private_key``: defines the name of the private key to be used
  to connect to the client;

* ``db_name``: defines the name of the database to dump;

Backing up a file server
++++++++++++++++++++++++

.. code-block:: ini

  [srvfiles-home]
  type=rsync+ssh
  server_name=srvfiles
  remote_dir=/home
  private_key=/root/.ssh/id_dsa
  exclude_list=".mozilla",".thunderbird",".x2go","*.avi"
  bwlimit = 100

Mandatory parameters:

* ``[srvfiles-home]``: name of the section starts
  with the name you give to it;

* ``type``: specifies the backup type for the Mysql database dump;

* ``server_name``: defines the server to be backed up
  by its DNS name or IP address;

* ``remote_dir``: defines the folder on the remote host to backup;

* ``private_key``: defines the name of the private key to be used
  to connect to the client;

  .. attention::

    In case of Windows client, specificities are to be expected:

    By default we use the root user for backups, for windows we will use
    the Administrator account (pay attention to the sensitive box).

    .. code-block:: ini

      remote_user=Administrator

    Through :program:`cygwin`, the directory to be backed up will always start
    with :file:`/cygdrive`, so it must be specified
    in the ``remote_dir`` parameter.

    .. code-block:: ini

      remote_dir=/cygdrive/c/WINDOWS/

.. hint::

  Other non-mandatory parameters can be used. The ``listdrivers`` option
  allows you to see them. The two most frequently used parameters are:

  * ``exclude_list``: defines the files to be excluded from the backup;

  * ``bwlimit``: defines the maximum speed of the backup;

Backing up a XenCenter virtual machine
++++++++++++++++++++++++++++++++++++++

On local storage
""""""""""""""""

.. code-block:: ini

  [wsmanage]
  type=xen-xva
  xcphost=srvxen1
  server_name=wsmanage
  password_file=/root/xen_passwd
  backup_retention_time=2
  halt_vm=True
  enable_https=False

Mandatory parameters:

* ``[wsmanage]``: name of the section starts
  with the name you give to it;

* ``type``: specifies the backup type for the Mysql database dump;

* ``xcphost``: defines the XCP server where the VM is found by its DNS name or IP;

* ``server_name``: defines the server to be backed up
  by its DNS name or IP address;

* ``password_file``: defines a file where are stored the user and the password
  to be used for exporting the :mimetype:`.xva` file;

* ``backup_retention_time``: defines the maximum number of exports
  for the virtual machine;

* ``halt_vm``: **True** = stop the virtual machine then export,
  **False** = snapshot the virtual machine then export the :file:`xva`
  without stopping the virtual machine;

* ``enable_https``: activate or deactivate https protocol for transfer;

On remote storage
"""""""""""""""""

.. code-block:: ini

  [srvads-copy]
  type=copy-vm-xcp
  server_name=srvxen1
  vm_name=srvads
  storage_name=iscsi-sr1
  password_file=/root/xen_passwd
  network_name=test-dcardon
  max_copies=3

Mandatory parameters:

* ``[srvads-copy]``: name of the section starts
  with the name you give to it;

* ``type``: specifies the backup type for the Mysql database dump;

* ``server_name``: defines the server to be backed up
  by its DNS name or IP address;

* ``vm_name``: defines the virtual machine to be backed up
  (its name-label in XCP);

* ``storage_name``: defines the storage to where to copy the virtual machine
  (its name-label in XCP);

* ``password_file``: defines a file where are stored the user and the password
  to be used for exporting the :mimetype:`.xva` file;

* ``network_name``: defines the network to which to copy the VM
  (its name-label in XCP);

* ``max_copies``: maximum number of exports for the virtual machine;

XenCenter metadata
""""""""""""""""""

.. code-block:: ini

[srvxen1-metadata]
type=xcp-dump-metadata
server_name=srvxen1
password_file=/root/xen_passwd

Mandatory parameters:

* ``[srvxen1-metadata]``: name of the section starts
  with the name you give to it;

* ``type``: specifies the backup type for the Mysql database dump;

* ``server_name``: defines the server to be backed up
  by its DNS name or IP address;

* ``password_file``: defines a file where are stored the user and the password
  to be used for exporting the :mimetype:`.xva` file;

.. attention::

  For maximum security put the password file in the root directory
  with read-write access only for it.

  .. code-block:: bash

    vi /root/xen_passwd

  example of the content of the file:

  .. code-block:: ini

    user
    password

  implementation of restricted rights

  .. code-block:: bash

    chmod 600 /root/xen_passwd
