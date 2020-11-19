.. Reminder for header structure:
  Level 1: ====================
  Level 2: --------------------
  Level 3: ++++++++++++++++++++
  Level 4: """"""""""""""""""""
  Level 5: ^^^^^^^^^^^^^^^^^^^^

.. meta::
  :description: TISBackup Documentation
  :keywords: Documentation, TISBackup, introduction, welcome page, Welcome

.. |date| date::

The objective of TISbackup is to benefit from file backups
and centralized alert feedback on "reasonable" data volumes
(of the order of a few TB).

TISBackup allows:

* to know if a recent backup exists;

* to keep a history with deduplication at the file level (no duplicate backups);

* to have an immediate view of the contents of a server or a server area
  for data restoration ;

* to export the last backup to an external media in order to transfer
  it to a secure location;

* to configure the backup cycle with a simple
  and readable :mimetype:`.ini` file;

* to work with a module mechanism to extend the type of backups
  (https, rsync, postgres, mysql,) of virtual machines;

Satisfying these needs stems from the need for a tool
to manage a vast pool of machines each hosting a multitude
of different software or services (different editors,
different hardware platforms and operating environments, etc.).
Finally, as the backup procedures of a publisher changed without any warning,
the remote backup mechanisms were regularly broken, which caused us some scares
with the mechanisms we were using before.

Overview of existing solutions
==============================

Different open source solutions exist but did not meet our specifications.

Baccula
-------

:program:`Baccula` is a high-performance solution for full backups on tape
and removable media. However, a restore can take a long time
and the storage of a history can be voluminous.
The backup is saved on a file system that is not readable by a Windows system.
An uninitiated "backup manager" will not be able to check the contents
of his backup from home.

r-snapshot
----------

:program:`r-snapshot` almost corresponds to the specifications
but is complex to configure and any necessary modification
would have been difficult to develop as an overlay of the existing one:

* the backups are organized by date then by zone which is the opposite
  of what was desired;

* it is not possible to configure different backup frequencies
  according to the criticality levels of the servers;

* finally, the deletion of obsolete backups is done in the same process
  as the backups, which can be very long and can be problematic
  if there is a problem during the backup.

**... and now TISbackup ...**

.. toctree::
  :maxdepth: 2
  :caption: Presenting TISBackup

  presenting_tisbackup.rst
  installing_tisbackup.rst
  configuring_tisbackup.rst
  using_tisbackup.rst

.. toctree::
  :maxdepth: 1
  :caption: Appendix

  tranquil-it-contacts.rst
  screenshots.rst

Indices and tables
==================

* :ref:`genindex`

* :ref:`search`
