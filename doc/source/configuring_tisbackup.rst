.. Reminder for header structure:
  Level 1: ====================
  Level 2: --------------------
  Level 3: ++++++++++++++++++++
  Level 4: """"""""""""""""""""
  Level 5: ^^^^^^^^^^^^^^^^^^^^

.. meta::
  :description: Configuring the backup jobs
  :keywords: Documentation, TISBackup, configuration, backup jobs

.. |clap| image:: wapt-resources/clapping-hands-microsoft.png
  :scale: 50%
  :alt: Clapping hands

Configuring the backup jobs
===========================

.. _configuring_backup_jobs:

The configuration of the backups is done in an :mimetype:`.ini` file,
by default :file:`/etc/tis/tisbackup-config.ini`:

* a global section where general parameters are specified;

* then for each backup a section will be created;
