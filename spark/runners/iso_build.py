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

from spark.utils.schroot import spark_schroot, chroot_run_logged, make_commandfile, chroot_copy


class IsoBuilder:

    def __init__(self):
        pass

    def set_job(self, job, workspace):
        self._job_id = job.get('_id')
        self._job_data = job
        self._workspace = workspace

        suite_name = job.get('suite')
        arch = job.get('architecture')
        if not suite_name:
            return False
        if not arch:
            return False

        self._chroot_name = '{0}-{1}'.format(suite_name, arch)
        return True

    def run(self, jlog):
        with spark_schroot(self._chroot_name, self._job_id) as (chroot, wsdir, results_dir):

            # install git
            ret = chroot_run_logged(chroot, jlog, [
                'apt-get', 'install', '-y', 'git', 'ca-certificates'
            ], user='root')
            if ret:
                return False

            # we also want live-build to be present
            ret = chroot_run_logged(chroot, jlog, [
                'apt-get', 'install', '-y', 'live-build'
            ], user='root')
            if ret:
                return False

            # construct build recipe
            commands = []
            commands.append('cd {}'.format(wsdir))
            commands.append('git clone --depth=2 {0} {1}/lb'.format(self._job_data.get('liveBuildGit'), wsdir))
            commands.append('cd ./lb')

            for cmd in self._job_data.get('commands'):
                commands.append(cmd)

            # save artifacts
            commands.append('mv *.iso {}/'.format(results_dir))
            commands.append('mv -f *.zsync {}/'.format(results_dir))
            commands.append('mv -f *.contents {}/'.format(results_dir))
            commands.append('mv -f *.files {}/'.format(results_dir))
            commands.append('mv -f *.packages {}/'.format(results_dir))
            commands.append('mv -f *.b2sums {}/'.format(results_dir))
            commands.append('mv -f *.sha256sums {}/'.format(results_dir))

            with make_commandfile(self._job_id, commands) as shfname:
                chroot_copy(chroot, shfname, shfname)
                ret = chroot_run_logged(chroot, jlog, [
                    'chmod', '+x', shfname
                ], user='root')
                if ret:
                    return False

                ret = chroot_run_logged(chroot, jlog, [
                    shfname
                ], user='root')
                if ret:
                    return False

            if ret:
                return False
        return True
