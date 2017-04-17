#!/bin/sh
set -e
set -x
export LANG=C.UTF-8

#
# This script is supposed to run inside the Laniakea Docker container
# on the CI system.
#

mkdir build && cd build
meson -Dmaintainer=true ..
ninja

# Test Install
DESTDIR=/tmp/lk-root ninja install

ninja test
