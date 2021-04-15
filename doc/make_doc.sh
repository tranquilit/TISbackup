#!/bin/sh
set -e

export http_proxy=http://srvproxy:8080
export https_proxy=http://srvproxy:8080

echo "clean"
make clean

rm -Rf ./build/

make clean

echo "make html English"
make htmlen

cp ./robots.txt build/en/doc
mkdir ./build/en/doc/.well-known
cp security.txt ./build/en/doc/.well-known
touch ./build/en/doc/.nojekyll
