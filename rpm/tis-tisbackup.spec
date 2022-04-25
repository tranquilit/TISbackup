%define _topdir   .
%define buildroot ./builddir
%define VERSION %(cat __VERSION__)

Name:	        tis-tisbackup
Version:        %{VERSION}
Release:	1%{?dist}
Summary:	TisBackup backup manager
BuildArch:	x86_64

Group:          System Environment/Daemons
License:	GPL
URL:		http://dev.tranquil.it
Source0:	../
Prefix:		/

%if  "%{rhel}" == "8"
Requires:  unzip rsync python3-paramiko python3-pyvmomi nfs-utils  python3-flask python3-simplejson autofs python3-pexpect 
%endif
%if "%{rhel}" == "7"
Requires:  unzip rsync python36-paramiko python3-pyvmomi nfs-utils  python3-flask python3-simplejson autofs pexpect
%endif

%description

%install
set -ex

mkdir -p %{buildroot}/opt/tisbackup/lib
mkdir -p %{buildroot}/usr/lib/systemd/system/
mkdir -p %{buildroot}/etc/cron.d/
mkdir -p %{buildroot}/etc/tis
mkdir -p %{buildroot}/usr/bin/

pip3 install -r ../../requirements.txt -t %{buildroot}/opt/tisbackup/lib

rsync --exclude "deb/" --exclude "doc/" --exclude "rpm/" --exclude ".git"  -aP ../../  %{buildroot}/opt/tisbackup/
rsync -aP ../../scripts/tisbackup_gui.service  %{buildroot}/usr/lib/systemd/system/
rsync -aP ../../scripts/tisbackup_huey.service  %{buildroot}/usr/lib/systemd/system/
rsync -aP ../../samples/tisbackup.cron  %{buildroot}/etc/cron.d/tisbackup
rsync -aP ../../samples/tisbackup_gui.ini  %{buildroot}/etc/tis
rsync -aP ../../samples/tisbackup-config.ini.sample  %{buildroot}/etc/tis/tisbackup-config.ini.sample
ln -s /opt/tisbackup/tisbackup.py  %{buildroot}/usr/bin/tisbackup

%files
%defattr(-,root,root)
%attr(-,root,root)/opt/tisbackup/
%attr(-,root,root)/usr/lib/systemd/system/tisbackup_gui.service
%attr(-,root,root)/usr/lib/systemd/system/tisbackup_huey.service
%attr(-,root,root)/etc/tis
%attr(-,root,root)/etc/cron.d/tisbackup
%attr(-,root,root)/usr/bin/tisbackup

%pre


%post
python3 -m compileall  /opt/tisbackup/
find /opt/tisbackup -name "*.pyc" -exec rm -rf {} \;

%postun
rm -rf /opt/tisbackup
