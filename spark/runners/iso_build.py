# -*- coding: utf-8 -*-
#
# Copyright (C) 2017 Matthias Klumpp <matthias@tenstral.net>
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

import shlex
from spark.utils.schroot import spark_schroot, chroot_run_logged, make_commandfile, chroot_copy, chroot_upgrade


def run(jlog, job, jdata):
    suite_name = jdata.get('suite')
    arch = job.get('architecture')
    if not suite_name:
        return False, None, None
    if not arch:
        return False, None, None

    chroot_name = '{0}-{1}'.format(suite_name, arch)

    with spark_schroot(chroot_name, jlog.job_id) as (chroot, wsdir, results_dir):
        chroot_upgrade(chroot, jlog)

        # install git
        ret = chroot_run_logged(chroot, jlog, [
           'apt-get', 'install', '-y', 'git', 'ca-certificates'
        ], user='root')
        if ret:
            return False, None, None

        # we also want live-build to be present
        ret = chroot_run_logged(chroot, jlog, [
           'apt-get', 'install', '-y', 'live-build'
        ], user='root')
        if ret:
            return False, None, None

        # construct build recipe
        # preamble
        commands = []
        commands.append('export DEBIAN_FRONTEND=noninteractive')

        commands.append('cd {}'.format(wsdir))
        commands.append('git clone --depth=2 {0} {1}/lb'.format(shlex.quote(self._job_data.get('live_build_git')), wsdir))
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
        results_dir = '/workspaces/{}/artifacts'.format(job_id)
        commands.append('mv *.iso {}/'.format(results_dir))
        commands.append('mv -f *.zsync {}/'.format(results_dir))
        commands.append('mv -f *.contents {}/'.format(results_dir))
        commands.append('mv -f *.files {}/'.format(results_dir))
        commands.append('mv -f *.packages {}/'.format(results_dir))
        commands.append('mv -f *.b2sum {}/'.format(results_dir))
        commands.append('mv -f *.sha256sum {}/'.format(results_dir))

        with make_commandfile(jlog.job_id, commands) as shfname:
            chroot_copy(chroot, shfname, shfname)

            ret = chroot_run_logged(chroot, jlog, [
                'sh', '-e', shfname
            ], user='root')
            if ret:
                return False, None, None

        if ret:
            return False, None, None

    # collect list of files to upload
    files = []
    for f in glob.glob('result/*'):
        files.append(f)

    return True, files, None
