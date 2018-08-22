# -*- coding: utf-8 -*-
#
# Copyright (C) 2017-2018 Matthias Klumpp <matthias@tenstral.net>
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
import glob
import shlex
from spark.utils.workspace import make_commandfile, debspawn_run_commandfile


def get_version():
    return ('isobuild', '0.1')


def run(jlog, job, jdata):
    suite_name = jdata.get('suite')
    arch = job.get('architecture')
    if not suite_name:
        return False, None, None
    if not arch:
        return False, None, None

    job_id = jlog.job_id

    # construct build recipe
    # prerequisites
    commands = []
    commands.append('export DEBIAN_FRONTEND=noninteractive')

    commands.append('apt-get install -y git ca-certificates')
    commands.append('apt-get install -y live-build')

    # preamble
    wsdir = '/srv/build/'
    commands.append('cd {}'.format(wsdir))
    commands.append('git clone --depth=2 {0} {1}/lb'.format(shlex.quote(jdata.get('live_build_git')), wsdir))
    commands.append('cd ./lb')

    # flavor env var
    flavor = jdata.get('flavor')
    if flavor:
        commands.append('export FLAVOR="{}"'.format(shlex.quote(flavor)))

    # the actual build commands
    commands.append('lb config')
    commands.append('lb build')

    commands.append('b2sum *.iso *.contents *.zsync *.packages > checksums.b2sum')
    commands.append('sha256sum *.iso *.contents *.zsync *.packages > checksums.sha256sum')

    # save artifacts (move to internal bindmounted directory)
    results_dir = '/srv/artifacts'.format(job_id)
    commands.append('mv *.iso {}/'.format(results_dir))
    commands.append('mv -f *.zsync {}/'.format(results_dir))
    commands.append('mv -f *.contents {}/'.format(results_dir))
    commands.append('mv -f *.files {}/'.format(results_dir))
    commands.append('mv -f *.packages {}/'.format(results_dir))
    commands.append('mv -f *.b2sum {}/'.format(results_dir))
    commands.append('mv -f *.sha256sum {}/'.format(results_dir))

    with make_commandfile(jlog.job_id, commands) as shfname:
        ret, _ = debspawn_run_commandfile(jlog,
                                          suite_name,
                                          arch,
                                          build_dir=None,
                                          artifacts_dir=os.path.abspath('result/'),
                                          command_script=shfname,
                                          header='ISO image build for {}'.format(flavor))
        if ret:
            return False, None, None

    if ret:
        return False, None, None

    # collect list of files to upload
    files = []
    for f in glob.glob('result/*'):
        files.append(os.path.abspath(f))

    return True, files, None
