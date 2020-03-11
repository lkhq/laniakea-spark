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
    return ('imagebuild', '0.1')


def build_iso_image(jlog, job, jdata):
    '''
    Build an ISO image using live-build
    '''
    suite_name = jdata.get('suite')
    arch = job.get('architecture')

    # construct build recipe
    # prerequisites
    commands = []
    commands.append('export DEBIAN_FRONTEND=noninteractive')

    commands.append('apt-get install -yq --no-install-recommends git ca-certificates')
    commands.append('apt-get install -yq live-build')

    # preamble
    wsdir = '/srv/build/'
    commands.append('cd {}'.format(wsdir))
    commands.append('git clone --depth=2 {0} {1}/lb'.format(shlex.quote(jdata.get('git_url')), wsdir))
    commands.append('cd ./lb')

    # set suite to build image for
    commands.append('export SUITE="{}"'.format(shlex.quote(suite_name)))

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
    results_dir = '/srv/artifacts'
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
                                          artifacts_dir=os.path.abspath('artifacts/'),
                                          command_script=shfname,
                                          header='ISO image build for {} {}'.format(suite_name, flavor))
    if ret != 0:
        return False, None, None

    # collect list of files to upload
    files = []
    for f in glob.glob('artifacts/*'):
        files.append(os.path.abspath(f))

    return True, files, None


def build_disk_image(jlog, job, jdata):
    '''
    Build disk images using custom tooling PureOS uses.
    FIXME: Can this be a bit more generic, possibly using just
    # one of vmdb2/debos/etc. in future?
    '''
    suite_name = jdata.get('suite')
    arch = job.get('architecture')

    # construct build recipe
    # prerequisites
    commands = []
    commands.append('export DEBIAN_FRONTEND=noninteractive')

    commands.append('apt-get install -yq --no-install-recommends git ca-certificates')
    commands.append('apt-get install -yq xz-utils debootstrap')
    commands.append('apt-get install -yq --no-install-recommends vmdb2')
    if arch == 'amd64':
        commands.append('apt-get install -yq debos')

    # preamble
    wsdir = '/srv/build/'
    commands.append('cd {}'.format(wsdir))
    commands.append('git clone --depth=2 {0} {1}/imgbuild'.format(shlex.quote(jdata.get('git_url')), wsdir))
    commands.append('cd ./imgbuild')

    # the flavor variable is used to encode the board type as well
    flavor = jdata.get('flavor')
    if flavor:
        commands.append('export FLAVOR="{}"'.format(shlex.quote(flavor)))
    parts = flavor.split('-', 2)
    board_type = None
    if len(parts) >= 3:
        board_type = parts[-1]

    # the actual build commands
    img_build_cmd = './build-image -d {}'.format(suite_name)
    if board_type:
        img_build_cmd = '{} -b {}'.format(img_build_cmd, board_type)

    # run the "image-build" script if it exists, otherwise assume a Makefile is there
    # which does the right thing and just run make
    commands.append('if [ -f "build-image" ]')
    commands.append('then')
    commands.append(img_build_cmd)
    commands.append('else')
    commands.append('make')
    commands.append('fi')

    commands.append('xz $(find . -maxdepth 1 -type f \\( -name "*.img" -o -name "*.qcow2" \\) -print)')

    commands.append('compressed_images=$(find . -maxdepth 1 -type f \\( -name "*.img.xz" -o -name "*.qcow2.xz" \\) -print)')
    commands.append('b2sum $compressed_images > {}-checksums.b2sum'.format(flavor.replace(' ', '')))
    commands.append('sha256sum $compressed_images > {}-checksums.sha256sum'.format(flavor.replace(' ', '')))

    # save artifacts (move to internal bindmounted directory)
    results_dir = '/srv/artifacts'
    commands.append('mv $compressed_images {}/'.format(results_dir))
    commands.append('mv -f *.b2sum {}/'.format(results_dir))
    commands.append('mv -f *.sha256sum {}/'.format(results_dir))

    with make_commandfile(jlog.job_id, commands) as shfname:
        ret, _ = debspawn_run_commandfile(jlog,
                                          suite_name,
                                          arch,
                                          build_dir=None,
                                          artifacts_dir=os.path.abspath('artifacts/'),
                                          command_script=shfname,
                                          header='Disk image build for {}'.format(flavor),
                                          allow_dev_access=True)
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
    image_kind = jdata.get('image_kind')
    if not suite_name:
        return False, None, None
    if not arch:
        return False, None, None

    if image_kind == 'iso':
        return build_iso_image(jlog, job, jdata)
    elif image_kind == 'img':
        return build_disk_image(jlog, job, jdata)

    return False, None, None
