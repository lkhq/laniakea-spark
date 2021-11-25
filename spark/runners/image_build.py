# -*- coding: utf-8 -*-
#
# Copyright (C) 2017-2021 Matthias Klumpp <matthias@tenstral.net>
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

from spark.utils.command import safe_run, run_logged
from spark.utils.workspace import make_commandfile, debspawn_run_commandfile


def get_version():
    return ('imagebuild', '0.1')


def build_image(jlog, host_arch: str, job, jdata):
    '''
    Build an image using the provided recipe (usually utilizing debos)
    '''
    distro_name = jdata.get('distribution')
    suite_name = jdata.get('suite')
    build_arch = jdata.get('architecture')
    image_format = jdata.get('image_format', 'iso')
    env_name = jdata.get('environment')
    image_style = jdata.get('style')

    # clone the image build recipe repository
    safe_run(['git', 'clone', '--depth=1', jdata.get('git_url'), 'ib'])
    run_logged(jlog, ['git', 'log', '--pretty=oneline', '-1'], cwd=os.path.abspath('ib'))

    # test if we have a prepare script and something to cache
    init_script = os.path.join('ib', 'prepare.sh')
    init_commands = []
    cache_key = None
    if os.path.isfile(init_script):
        cache_key = 'mkimage-{}-{}-{}'.format(
            image_format, env_name if env_name else 'any', image_style if image_style else 'any'
        )
        init_commands.append('export DEBIAN_FRONTEND=noninteractive')
        init_commands.append('cd /srv/build')
        init_commands.append('exec ./prepare.sh')

    # construct build recipe
    if not os.path.isfile(os.path.join('ib', 'build.sh')):
        raise Exception('No "build.sh" script found to build the image')
    commands = []
    commands.append('export DEBIAN_FRONTEND=noninteractive')
    commands.append('export IB_SUITE="{}"'.format(shlex.quote(suite_name)))
    commands.append('export IB_ENVIRONMENT="{}"'.format(shlex.quote(env_name)))
    commands.append('export IB_IMAGE_STYLE="{}"'.format(shlex.quote(image_style)))
    commands.append('export IB_TARGET_ARCH="{}"'.format(shlex.quote(build_arch)))
    commands.append('systemd-machine-id-setup')
    commands.append('cd /srv/build')
    commands.append('exec ./build.sh')

    with make_commandfile(jlog.job_id, init_commands) as shi_fname:
        with make_commandfile(jlog.job_id, commands) as shc_fname:
            ret, _ = debspawn_run_commandfile(
                jlog,
                suite_name,
                host_arch,
                build_dir=os.path.abspath('ib'),
                artifacts_dir=os.path.abspath('artifacts'),
                init_script=shi_fname if init_commands else None,
                command_script=shc_fname,
                header='{} {} image build for {} {} [{}]'.format(
                    distro_name, image_format.upper(), suite_name, env_name, image_style
                ),
                allow_kvm=True,
                cache_key=cache_key,
            )
    if ret != 0:
        return False, None, None

    # collect list of files to upload
    files = []
    for f in glob.glob('artifacts/*'):
        files.append(os.path.abspath(f))

    return True, files, None


def run(jlog, job, jdata):
    suite_name = jdata.get('suite')
    arch = job.get('architecture')
    if not suite_name:
        return False, None, None
    if not arch:
        return False, None, None

    return build_image(jlog, arch, job, jdata)
