#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2018-2024 Matthias Klumpp <matthias@tenstral.net>
#
# SPDX-License-Identifier: LGPL-3.0-or-later

#
# This is a helper script to install additional configuration and documentation into
# system locations, which Python's setuptools and pip will not usually let us install.
#

import os
import sys
import shutil
from pathlib import Path
from argparse import ArgumentParser
from tempfile import TemporaryDirectory

try:
    import pkgconfig
except ImportError:
    print()
    print(
        (
            'Unable to import pkgconfig. Please install the module '
            '(apt install python3-pkgconfig or pip install pkgconfig) '
            'to continue.'
        )
    )
    print()
    sys.exit(4)


class Installer:
    def __init__(self, root: str = None, prefix: str = None):
        if not root:
            root = os.environ.get('DESTDIR')
        if not root:
            root = '/'
        self.root = root

        if not prefix:
            prefix = '/usr/local' if self.root == '/' else '/usr'
        if prefix.startswith('/'):
            prefix = prefix[1:]
        self.prefix = prefix

    def install(self, src, dst, replace_vars=False):
        if dst.startswith('/'):
            dst = dst[1:]
            dst_full = os.path.join(self.root, dst, os.path.basename(src))
        else:
            dst_full = os.path.join(self.root, self.prefix, dst, os.path.basename(src))
        if dst_full.endswith('.in'):
            dst_full = dst_full[:-3]

        Path(os.path.dirname(dst_full)).mkdir(mode=0o755, parents=True, exist_ok=True)
        if replace_vars:
            with open(src, 'r') as f_src:
                with open(dst_full, 'w') as f_dst:
                    for line in f_src:
                        f_dst.write(line.replace('@PREFIX@', '/' + self.prefix))
        else:
            shutil.copy(src, dst_full)
        os.chmod(dst_full, 0o644)
        print('{}\t\t{}'.format(os.path.basename(src), dst_full))


def chdir_to_source_root():
    thisfile = __file__
    if not os.path.isabs(thisfile):
        thisfile = os.path.normpath(os.path.join(os.getcwd(), thisfile))
    os.chdir(os.path.dirname(thisfile))


def install_data(temp_dir: str, root_dir: str, prefix_dir: str):
    chdir_to_source_root()

    print('Checking dependencies')
    if not pkgconfig.installed('systemd', '>= 240'):
        print('Systemd is not installed on this system. Please make systemd available to continue.')
        sys.exit(4)

    print('Installing data')
    inst = Installer(root_dir, prefix_dir)
    sd_system_unit_dir = pkgconfig.variables('systemd')['systemdsystemunitdir']

    inst.install('data/systemd/laniakea-spark.service.in', sd_system_unit_dir, replace_vars=True)
    inst.install('data/sudo/10laniakea-spark', '/etc/sudoers.d/', replace_vars=True)


def main():
    parser = ArgumentParser(description='LkSpark system data installer')

    parser.add_argument(
        '--root', action='store', dest='root', default=None, help='Root directory to install into.'
    )
    parser.add_argument(
        '--prefix',
        action='store',
        dest='prefix',
        default=None,
        help='Directory prefix (usually `/usr` or `/usr/local`).',
    )

    options = parser.parse_args(sys.argv[1:])
    with TemporaryDirectory(prefix='dsinstall-') as temp_dir:
        install_data(temp_dir, options.root, options.prefix)
    return 0


if __name__ == '__main__':
    sys.exit(main())
