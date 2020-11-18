#!/bin/sh
set -e

export http_proxy=http://srvproxy:8080
export https_proxy=http://srvproxy:8080

echo "clean"
make clean

rm -Rf ./build/

echo "gettext and update po"
make gettext
sphinx-intl update -p build/locale/ -l fr

make clean

echo "make html English"
make htmlen

echo "make html French"
make -e SPHINXOPTS="-D language='fr'" htmlfr

echo "make epub EN"
make epub_en

echo "make epub FR"
make -e SPHINXOPTS="-D language='fr'" epub_fr

echo "make latexpdf EN"
# we ignore errors from that build for now
make latexpdf_en  || true

echo "make latexpdf FR"
make -e SPHINXOPTS="-D language='fr'" latexpdf_fr || true

cp ./robots.txt build/en/doc
cp ./robots.txt build/fr/doc
mkdir ./build/en/doc/.well-known
mkdir ./build/fr/doc/.well-known
cp security.txt ./build/en/doc/.well-known
cp security.txt ./build/en/doc/.well-known
