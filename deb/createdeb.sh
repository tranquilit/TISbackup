#!/usr/bin/env bash

VERSION_DEB=$(cat /etc/debian_version | cut -d "." -f 1) 
VERSION_SHORT=$(cat ../tisbackup.py  | grep "__version__" | cut -d "=" -f 2 | sed 's/"//g')
GIT_COUNT=`git rev-list HEAD --count` 
VERSION="${VERSION_SHORT}.${GIT_COUNT}-deb${VERSION_DEB}"

rm -f *.deb
rm -Rf builddir
mkdir builddir
mkdir builddir/DEBIAN
cp ./control ./builddir/DEBIAN
cp ./postinst ./builddir/DEBIAN
cp ./prerm ./builddir/DEBIAN
cp ./postrm ./builddir/DEBIAN

sed "s/__VERSION__/$VERSION/" -i ./builddir/DEBIAN/control

mkdir -p ./builddir/opt/tisbackup/
mkdir -p ./builddir/usr/lib/systemd/system/
mkdir -p ./builddir/etc/tis
mkdir -p ./builddir/etc/cron.d/

pip3 install -r ../requirements.txt -t ./builddir/opt/tisbackup/lib
pip3 install huey==0.4.9
pip3 install redis

rsync -aP --exclude "deb/" --exclude "doc/" --exclude "rpm/" --exclude ".git" ../ ./builddir/opt/tisbackup
rsync -aP ../scripts/tisbackup_gui.service  ./builddir/usr/lib/systemd/system/
rsync -aP ../scripts/tisbackup_huey.service  ./builddir/usr/lib/systemd/system/
rsync -aP ../samples/tisbackup_gui.ini  ./builddir/etc/tis
rsync -aP ../samples/tisbackup-config.ini.sample  ./builddir/etc/tis/tisbackup-config.ini.sample

chmod 755 ./builddir/opt/tisbackup/tisbackup.py

dpkg-deb --build builddir tis-tisbackup-1-${VERSION}.deb


