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

import os
import logging as log
from contextlib import contextmanager
from tempfile import NamedTemporaryFile
from spark.utils.command import run_logged


@contextmanager
def lkworkspace(wsdir):
    import shutil
    artifacts_dir = os.path.join(wsdir, 'artifacts')
    if not os.path.exists(artifacts_dir):
        os.makedirs(artifacts_dir)
    results_dir = os.path.join(wsdir, 'result')
    if not os.path.exists(results_dir):
        os.makedirs(results_dir)

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
    f.write('set -x\n')
    f.write('\n')
    for cmd in commands:
        f.write(cmd + '\n')
    f.flush()
    yield f.name
    f.close()


def debspawn_run_commandfile(jlog, suite, arch, build_dir, artifacts_dir, command_script, header=None, allow_dev_access=False):
    '''
    Execute a command-script file in a debspawn container.
    '''

    ds_cmd = ['debspawn',
              'run',
              '--external-command',
              '--arch={}'.format(arch)]
    if artifacts_dir:
        ds_cmd.append('--artifacts-out={}'.format(artifacts_dir))
    if build_dir:
        ds_cmd.append('--build-dir={}'.format(build_dir))
    if allow_dev_access:
        ds_cmd.append('--allow={}'.format('full-dev-access'))

    if header:
        ds_cmd.append('--header={}'.format(header))
    ds_cmd.append(suite)
    ds_cmd.append(command_script)

    return run_logged(jlog, ds_cmd, True)
