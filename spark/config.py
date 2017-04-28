# Copyright (C) 2016 Matthias Klumpp <matthias@tenstral.net>
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

import json
import os
from pathlib import Path

'''
Local configuration for the spark daemon.
'''
class LocalConfig:
    CERTS_BASE_DIR = '/etc/laniakea/keys/curve/'

    def load(self, fname=None):
        if not fname:
            fname = '/etc/laniakea/spark.json'

        jdata = None
        with open(fname) as json_file:
            jdata = json.load(json_file)

        self._machine_id = Path('/etc/machine-id').read_text().strip('\n').strip()
        self._machine_name = jdata.get('MachineName')
        if not self._machine_name:
            self._machine_name = Path('/etc/hostname').read_text().strip('\n').strip()

        self._lighthouse_server = jdata['LighthouseServer']

        self._max_jobs = int(jdata.get("MaxJobs", 1))
        if self._max_jobs < 1:
            raise Exception('The maximum number of jobs can not be < 1.')

        self._client_cert_fname = os.path.join(self.CERTS_BASE_DIR, 'secret', '{0}_private.sec'.format(self.machine_name))
        self._server_cert_fname = os.path.join(self.CERTS_BASE_DIR, '{0}_lighthouse-server.pub'.format(self.machine_name))

    @property
    def machine_id(self) -> str:
        return self._machine_id

    @property
    def machine_name(self) -> str:
        return self._machine_name

    @property
    def lighthouse_server(self) -> str:
        return self._lighthouse_server

    @property
    def max_jobs(self) -> int:
        return self._max_jobs

    @property
    def client_cert_fname(self) -> str:
        return self._client_cert_fname

    @property
    def server_cert_fname(self) -> str:
        return self._server_cert_fname
