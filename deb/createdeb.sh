#!/usr/bin/env bash
VERSION=`git rev-list HEAD --count` 

rm -f *.deb
rm -Rf builddir
mkdir builddir
mkdir builddir/DEBIAN
cp ./control ./builddir/DEBIAN
cp ./files/postinst ./builddir/DEBIAN

sed "s/VERSION/$VERSION/" -i ./builddir/DEBIAN/control

mkdir -p builddir/opt/tisbackup/
mkdir -p ./builddir/usr/lib/systemd/system/
mkdir -p ./builddir/etc/tis
mkdir -p ./builddir/etc/cron.d/

rsync -aP --exclude="rpm" --exclude=".git" --exclude=deb ../ ./builddir/opt/tisbackup
rsync -aP ../scripts/tisbackup_gui.service  ./builddir/usr/lib/systemd/system/
rsync -aP ../scripts/tisbackup_huey.service  ./builddir/usr/lib/systemd/system/
rsync -aP ../samples/tisbackup.cron  ./builddir/etc/cron.d/tisbackup
rsync -aP ../samples/tisbackup_gui.ini  ./builddir/etc/tis
rsync -aP ../samples/tisbackup-config.ini.sample  ./builddir/etc/tis/tisbackup-config.ini.sample

chmod 755 /opt/tisbackup/tisbackup.py

dpkg-deb --build builddir tis-tisbackup-${VERSION}.deb


