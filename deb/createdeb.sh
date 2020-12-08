#!/usr/bin/env bash

VERSION_SHORT=$(cat ../tisbackup.py  | grep "__version__" | cut -d "=" -f 2 | sed 's/"//g')
GIT_COUNT=`git rev-list HEAD --count` 
VERSION="${VERSION_SHORT}.${GIT_COUNT}"

rm -f *.deb
rm -Rf builddir
mkdir builddir
mkdir builddir/DEBIAN
cp ./control ./builddir/DEBIAN
cp ./postinst ./builddir/DEBIAN

sed "s/__VERSION__/$VERSION/" -i ./builddir/DEBIAN/control

mkdir -p builddir/opt/tisbackup/
mkdir -p ./builddir/usr/lib/systemd/system/
mkdir -p ./builddir/etc/tis
mkdir -p ./builddir/etc/cron.d/

rsync -aP --exclude "deb/" --exclude "doc/" --exclude "rpm/" --exclude ".git" ../ ./builddir/opt/tisbackup
rsync -aP ../scripts/tisbackup_gui.service  ./builddir/usr/lib/systemd/system/
rsync -aP ../scripts/tisbackup_huey.service  ./builddir/usr/lib/systemd/system/
rsync -aP ../samples/tisbackup.cron  ./builddir/etc/cron.d/tisbackup
rsync -aP ../samples/tisbackup_gui.ini  ./builddir/etc/tis
rsync -aP ../samples/tisbackup-config.ini.sample  ./builddir/etc/tis/tisbackup-config.ini.sample
rsync -aP ../lib/huey/bin/huey_consumer.py  ./builddir/opt/tisbackup/

chmod 755 /opt/tisbackup/tisbackup.py

dpkg-deb --build builddir tis-tisbackup-1:${VERSION}.deb


