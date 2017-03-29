#!/usr/bin/env bash
#svn --username svnuser up
#VERSION=$(svn info |awk '/Revi/{print $2}')
VERSION=0.1
VERSION=$VERSION-$(git rev-parse --short HEAD)
rm -f *.deb
rm -Rf builddir
mkdir builddir
mkdir builddir/DEBIAN
cp ./control ./builddir/DEBIAN
#cp ./files/postinst ./builddir/DEBIAN
#cp ./files/prerm ./builddir/DEBIAN

sed "s/VERSION/$VERSION/" -i ./builddir/DEBIAN/control

mkdir -p builddir/opt/tisbackup/
mkdir -p ./builddir/usr/lib/systemd/system/

#cp ../scripts/tisbackup_gui.service ./builddir/usr/lib/systemd/system/
rsync -aP --exclude=deb ../ ./builddir/opt/tisbackup

#tis-arpwatch
#chmod 755 ./builddir/opt/tis-nagios/*.py
#chmod 755 ./builddir/etc/init.d/tis-arpwatch


dpkg-deb --build builddir tis-tisbackup-${VERSION}.deb

#echo "== Copie du .deb sur le serveur tisdeb =="
#scp *.deb root@srvinstallation:/var/www/srvinstallation/tisdeb/binary

#echo "== Scan du répertoire =="
#ssh root@srvinstallation /var/www/srvinstallation/tisdeb/updateRepo.sh

