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

import os
from schroot import schroot
from spark.utils import cd, chroot_run_logged


class IsoBuilder:

    def __init__(self):
        pass

    def set_job(self, job, workspace):
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
        with cd('/tmp'):
            with schroot(self._chroot_name) as chroot:
                ret = chroot_run_logged(chroot, jlog, [
                    'mkdir', '-p', '/srv/lb'
                ], user='root')
                if ret:
                    return False

                ret = chroot_run_logged(chroot, jlog, [
                    'apt-get', 'install', '-y', 'git'
                ], user='root')
                if ret:
                    return False

                ret = chroot_run_logged(chroot, jlog, [
                    'apt-get', 'install', '-y', 'live-build'
                ], user='root')

                if ret:
                    return False
        return True
