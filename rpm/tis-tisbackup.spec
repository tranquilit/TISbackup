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

Requires:       unzip rsync python-paramiko python-pyvmomi python-pip nfs-utils  python-flask python-setuptools python-simplejson autofs pexpect

# Turn off the brp-python-bytecompile script
#%global __os_install_post %(echo '%{__os_install_post}' | sed -e 's!/usr/lib[^[:space:]]*/brp-python-bytecompile[[:space:]].*$!!g')

%description

%install
set -ex

mkdir -p %{buildroot}/opt/tisbackup/
mkdir -p %{buildroot}/usr/lib/systemd/system/
mkdir -p %{buildroot}/etc/cron.d/
mkdir -p %{buildroot}/etc/tis

rsync --exclude="rpm" --exclude=".git" -aP ../../../tisbackup/  %{buildroot}/opt/tisbackup/
rsync -aP ../../../tisbackup/scripts/tisbackup_gui.service  %{buildroot}/usr/lib/systemd/system/
rsync -aP ../../../tisbackup/scripts/tisbackup_huey.service  %{buildroot}/usr/lib/systemd/system/
rsync -aP ../../../tisbackup/samples/tisbackup.cron  %{buildroot}/etc/cron.d/tisbackup
rsync -aP ../../../tisbackup/samples/tisbackup_gui.ini  %{buildroot}/etc/tis
rsync -aP ../../../tisbackup/samples/tisbackup-config.ini.sample  %{buildroot}/etc/tis/tisbackup-config.ini.sample
ln -s /opt/tisbackup/tisbackup.py /usr/bin/tisbackup

%files
%defattr(-,root,root)
%attr(-,root,root)/opt/tisbackup/
%attr(-,root,root)/usr/lib/systemd/system/
%attr(-,root,root)/etc/tis
%attr(-,root,root)/etc/cron.d/

%pre


%post
#[ -f /etc/dhcp/reservations.conf ] || touch /etc/dhcp/reservations.conf
#[ -f /etc/dhcp/reservations.conf.disabled ] || touch /etc/dhcp/reservations.conf.disabled
#[ -f /opt/tis-dhcpmanager/config.ini ] || cp /opt/tis-dhcpmanager/config.ini.sample /opt/tis-dhcpmanager/config.ini
#[ -f /etc/dhcp/reservations.conf ] && sed -i 's/{/{\n/;s/;/;\n/g;'  /etc/dhcp/reservations.conf &&  sed -i '/^$/d'  /etc/dhcp/reservations.conf

