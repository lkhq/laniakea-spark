# -*- coding: utf-8 -*-
#
# Copyright (C) 2018 Matthias Klumpp <matthias@tenstral.net>
#
# Licensed under the GNU Lesser General Public License Version 3
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the license, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>.

import logging as log
import os
import shlex
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from typing import Optional

from spark import __appname__, __version__
from spark.utils.command import run_logged


@contextmanager
def lkworkspace(wsdir):
    import shutil
    artifacts_dir = os.path.join(wsdir, 'artifacts')
    if not os.path.exists(artifacts_dir):
        os.makedirs(artifacts_dir)

    ncwd = os.getcwd()
    try:
        yield os.chdir(wsdir)
    finally:
        os.chdir(ncwd)
        try:
            shutil.rmtree(wsdir)
        except Exception as e:
            log.warning('Unable to remove stale workspace {0}: {1}'.format(wsdir, str(e)))


@contextmanager
def make_commandfile(job_id, commands):
    f = NamedTemporaryFile('w', suffix='.sh', prefix='{}-'.format(job_id))
    f.write('#!/bin/sh\n')
    f.write('set -e\n')
    f.write('export SPARK_ID="{}"\n'.format(shlex.quote(__appname__ + '-' + __version__)))
    f.write('set -x\n')
    f.write('\n')
    for cmd in commands:
        f.write(cmd + '\n')
    f.flush()
    yield f.name
    f.close()


def debspawn_run_commandfile(jlog, suite: str, arch: str, *,
                             build_dir: str, artifacts_dir: str, init_script: Optional[str] = None,
                             command_script: str, header=None, allow_kvm=False, cache_key: Optional[str] = None):
    '''
    Execute a command-script file in a debspawn container with optional initial environment caching.
    '''

    ds_cmd = ['debspawn',
              'run',
              '--external-command',
              '--arch={}'.format(arch)]
    if artifacts_dir:
        ds_cmd.extend(['--artifacts-out', artifacts_dir])
    if build_dir:
        ds_cmd.extend(['--build-dir', build_dir])
    if allow_kvm:
        ds_cmd.append('--allow={}'.format('kvm,read-kmods'))
    if cache_key:
        ds_cmd.extend(['--cachekey', '{}-{}'.format(suite, cache_key)])
    if init_script:
        ds_cmd.extend(['--init-command', init_script])

    if header:
        ds_cmd.append('--header={}'.format(header))
    ds_cmd.append(suite)
    ds_cmd.append(command_script)

    return run_logged(jlog, ds_cmd, True)
