#!/bin/sh

export http_proxy=http://srvproxy:8080
export https_proxy=http://srvproxy:8080

echo "clean"
make clean

echo "gettext"
make gettext

echo "sphinx update po"
sphinx-intl update -p build/locale/ -l fr

echo "make html English"
make htmlen
