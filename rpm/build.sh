#!/bin/sh

set -ex
rm -rf ./tis-tisbackup/ ./BUILD  *.rpm ./RPMS
mkdir -p BUILD RPMS

VERSION=`git rev-list HEAD --count` 
echo $VERSION > __VERSION__

rpmbuild -bb --buildroot $PWD/builddir -v --clean tis-tisbackup.spec
cp RPMS/*/*.rpm .

