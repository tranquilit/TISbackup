.. Reminder for header structure:
  Level 1: ====================
  Level 2: --------------------
  Level 3: ++++++++++++++++++++
  Level 4: """"""""""""""""""""
  Level 5: ^^^^^^^^^^^^^^^^^^^^

.. meta::
  :description: Installing and configuring TISBackup
  :keywords: Documentation, TISBackup, installation, configuration

.. |clap| image:: tisbackup-resources/clapping-hands-microsoft.png
  :scale: 50%
  :alt: Clapping hands

Installing and configuring TISBackup on Debian
==============================================

.. _base_debian_server_install:

Setting up the GNU/Linux Debian server
--------------------------------------

In order to install a fresh Debian Linux 11 *Bullseye* (physical or virtual)
without graphical interface, please refer to the
`Debian GNU/Linux Installation Guide <https://www.debian.org/releases/bullseye/amd64/>`_.

Configuring network parameters
++++++++++++++++++++++++++++++

.. include:: tisbackup-resources/linux-server-naming.txt

Configuring the name of the Debian server
+++++++++++++++++++++++++++++++++++++++++

.. hint::

  The short name of the future TISBackup server must not be longer
  than **15 characters** (the limit is due to *sAMAccountName* restriction
  in Active Directory).

The name of the TISBackup server must be a :abbr:`FQDN (Fully Qualified Domain Name)`,
that is to say it has both the server name and the DNS suffix.

* modify the :file:`/etc/hostname` file and write the FQDN of the server;

.. code-block:: bash

  # /etc/hostname of the TISBackup server
  srvbackup.mydomain.lan

* configure the :file:`/etc/hosts` file, be sure to put both the FQDN
  and the short name of the server;

.. code-block:: bash

  # /etc/hosts of the server
  127.0.0.1   localhost localhost.localdomain localhost4 localhost4.localdomain4
  ::1         localhost localhost.localdomain localhost6 localhost6.localdomain6
  10.0.0.10   srvbackup.mydomain.lan     srvbackup

.. hint::

  * on the line defining the DNS server IP address, be sure to have the IP
    of the server (not 127.0.0.1), then the FQDN, then the short name;

  * do not change the line with *localhost*;

Configuring the IP address of the Debian server
+++++++++++++++++++++++++++++++++++++++++++++++

* configure the IP address of the Debian Server
  in the :file:`/etc/network/interfaces`;

.. code-block:: bash

  # /etc/network/interfaces of the Debian server
  auto eth0
  iface eth0 inet static
    address 10.0.0.10
    netmask 255.255.255.0
    gateway 10.0.0.254

* apply the network configuration by rebooting the machine
  with a :code:`reboot`;

* if it has not already been done, create the DNS entry for the Server
  in the Organization's Active Directory;

* after reboot, configure the system language in English in order to have
  non-localized logs for easier searching of common errors;

.. code-block:: bash

  apt install locales-all
  localectl set-locale LANG=en_US.UTF-8
  localectl status

* check that the machine clock is on time (with NTP installed);

.. code-block:: bash

  dpkg -l | grep ntp
  service ntp status
  date

.. hint::

  If the NTP package is not installed.

  .. code-block:: bash

    apt install ntp
    systemctl enable ntp
    systemctl start ntp

* update and upgrade your Debian;

  .. code-block:: bash

    apt update
    apt upgrade -y

* install systemd;

  .. code-block:: bash

    apt install systemd

* restart the Debian server;

  .. code-block:: bash

     reboot

|clap| The Debian server is now ready. You may now go on to the next step
and :ref:`install TISBackup on your Debian<install_tisbackup_debian>`.

.. _install_tisbackup_debian:

Installing the TISBackup server
+++++++++++++++++++++++++++++++

From Tranquil IT's repository
"""""""""""""""""""""""""""""

The easiest way is to install the package from Tranquil IT repository :

.. tabs::

  .. code-tab:: bash On CentOS8 and derivate

    wget https://srvinstallation.tranquil.it/tisbackup/tis-tisbackup-162-1.el8.x86_64.rpm -O tis-tisbackup.rpm
    yum install -y tis-tisbackup.rpm

  .. code-tab:: bash On CentOS7

    wget https://srvinstallation.tranquil.it/tisbackup/tis-tisbackup-162-1.el7.x86_64.rpm -O tis-tisbackup.rpm
    yum install -y  tis-tisbackup.rpm

  .. code-tab:: bash On Debian 11

    wget https://srvinstallation.tranquil.it/tisbackup/tis-tisbackup-1-2.0.163-deb11.deb -O tis-tisbackup.deb
    apt install unzip python3-paramiko python3-pyvmomi python3-pexpect python3-flask python3-simplejson python3-pip
    dpkg -i tis-tisbackup.deb


From sources
""""""""""""

* install the required dependencies:

.. tabs::

  .. code-tab:: bash On CentOS8 and derivate

    unzip, ssh, rsync, python3-paramiko, python3-pyvmomi, python3-pexpect, python3-flask,python3-simplejson, python3-pip

  .. code-tab:: bash On CentOS7 and derivate

    unzip rsync python3-paramiko python3-pyvmomi nfs-utils  python3-flask python3-simplejson autofs python3-pexpect

  .. code-tab:: bash on Debian 11

    unzip rsync python36-paramiko python3-pyvmomi nfs-utils  python3-flask python3-simplejson autofs pexpect

* retrieve the git sources from https://github.com/tranquilit/TISbackup
  and place them in the :file:`/opt` folder on your server:

  .. code-block:: bash

    cd /opt/
    wget --no-check-certificate https://github.com/tranquilit/TISbackup/archive/master.zip
    unzip master.zip
    mv TISbackup-master tisbackup
    pip3 install huey iniparse -t /opt/tisbackup/lib
    chmod 755 /opt/tisbackup/tisbackup.py
    ln -sb /opt/tisbackup/tisbackup.py /usr/local/bin/tisbackup

* the :command:`tisbackup` command must return all *tisbackup* actions
  directly to you. For more information on the actions
  go to :ref:`the section on using TISBackup<using_tisbackup>`;

  .. code-block:: bash

    [root@srvbackup.mydomain.lan tisbackup]# tisbackup
    ERROR : You must provide one action to perform
    Usage: tisbackup -c configfile action

    TIS Files Backup system.

    action is either :
    backup : launch all backups or a specific one if -s option is used
    cleanup : removed backups older than retention period
    checknagios : check all or a specific backup against max_backup_age parameter
    dumpstat : dump the content of database for the last 20 backups
    retryfailed : try to relaunch the last failed backups
    listdrivers : list available backup types and parameters for config inifile
    exportbackup : copy lastest OK backups from local to location defined by --exportdir parameter
    register_existing : scan backup directories and add missing backups to database

Configuring TISBackup
+++++++++++++++++++++

* create the directory for TISBackup configuration files:

  .. code-block:: bash

    mkdir /etc/tis/

* in the directory :file:`/opt/tisbackup/samples/`, you will find the files
  :file:`config.ini.sample` and :file:`tisbackup-config.ini`
  which you can use as examples. Copy one of these two files
  into the :file:`/etc/tis` directory and we will describe in the next section
  how to customize this files;

  .. code-block:: bash

    cp /opt/tisbackup/samples/tisbackup-config.ini.sample /etc/tis/tisbackup-config.ini

Launching the backup scheduled task
+++++++++++++++++++++++++++++++++++

.. code-block:: bash

  cp /opt/tisbackup/samples/tisbackup.cron /etc/cron.d/tisbackup

* modify the :file:`/etc/cron.d/tisbackup` file to indicate when to launch
  the task;

Generating the public and private certificates
++++++++++++++++++++++++++++++++++++++++++++++

* as root:

  .. code-block:: bash

    ssh-keygen -t rsa -b 2048

* press :kbd:`Enter` for each one of the steps;

|clap| You may now go on to the next step
and :ref:`configure the backup jobs for your TISBackup<configuring_backup_jobs>`.

Setting up the graphical user interface for the TISBackup server
----------------------------------------------------------------

.. code-block:: bash

  cp /opt/tisbackup/samples/tisbackup_gui.ini /etc/tis/
  cp /opt/tisbackup/scripts/tisbackup_gui /etc/init.d/tisbackup_gui
  cp /opt/tisbackup/scripts/tisbackup_huey /etc/init.d/tisbackup_huey
  chmod +x /etc/init.d/tisbackup_gui
  chmod +x /etc/init.d/tisbackup_huey
  update-rc.d tisbackup_huey defaults
  update-rc.d tisbackup_gui defaults

You can now access your interface through the url
of your TISBackup server on port 8080.

.. figure:: tisbackup-resources/tisbackup_gui.png
  :align: center
  :scale: 100%
  :alt: TISBackup Web interface

  TISBackup Web interface
