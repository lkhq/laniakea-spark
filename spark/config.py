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

import json
import os
import platform
from typing import List
from pathlib import Path
import logging as log


class LocalConfig:
    """
    Local configuration for the spark daemon.
    """

    CERTS_BASE_DIR = '/etc/laniakea/keys/curve/'

    def load(self, fname=None):
        if not fname:
            fname = '/etc/laniakea/spark.json'

        jdata = None
        with open(fname) as json_file:
            jdata = json.load(json_file)

        self._machine_name = jdata.get('MachineName')
        if not self._machine_name:
            self._machine_name = Path('/etc/hostname').read_text().strip('\n').strip()

        # create machine ID from its name and the unique identifier it has
        machine_id_secret = Path('/etc/machine-id').read_text().strip('\n').strip()
        self._make_machine_id(machine_id_secret)

        self._lighthouse_server = jdata.get('LighthouseServer')
        if not self._lighthouse_server:
            raise Exception('The "LighthouseServer" configuration entry is missing. Please specify the address of a Lighthouse server.')

        self._max_jobs = int(jdata.get("MaxJobs", 1))
        if self._max_jobs < 1:
            raise Exception('The maximum number of jobs can not be < 1.')

        self._client_cert_fname = os.path.join(self.CERTS_BASE_DIR, 'secret', '{0}_private.sec'.format(self.machine_name))
        self._server_cert_fname = os.path.join(self.CERTS_BASE_DIR, '{0}_lighthouse-server.pub'.format(self.machine_name))

        workspace_root = jdata.get('WorkspaceRoot')
        if not workspace_root:
            workspace_root = '/var/lib/lkspark/'
        self._workspace_dir = os.path.join(workspace_root, 'workspaces')
        self._job_log_dir = os.path.join(workspace_root, 'logs')

        self._architectures = jdata.get("Architectures")
        if not self._architectures:
            import re
            # try to rescue doing some poor mapping to the Debian arch vendor strings
            # for a couple of common architectures
            machine_str = platform.machine()
            if machine_str == 'x86_64':
                self._architectures = ['amd64']
            elif re.match('i?86', machine_str):
                self._architectures = ['i386']
            else:
                self._architectures = [machine_str]
                log.warning('Using auto-detected architecture name: {}'.format(machine_str))

        self._dput_host = jdata.get('DputHost')
        if not self._dput_host:
            raise Exception('The essential "DputHost" configuration entry is missing.')
        self._gpg_key_uid = jdata.get('GpgKeyUID')
        if not self._dput_host:
            raise Exception('The essential "GpgKeyUID" configuration entry is missing.')


    def _make_machine_id(self, secret_id):
        bkey = self._machine_name + secret_id

        try:
            from hashlib import blake2b

            self._machine_id = blake2b(key=bkey.encode('utf-8'), digest_size=32).hexdigest()
        except ImportError:
            from hashlib import sha1
            # fall back to SHA1 - this sucks a bit, as the machine ID will change as soon
            # as the client has Python 3.6, so we should raise the minimum version requirement
            # as soon as we can.
            h = sha1()
            h.update(bkey.encode('utf-8'))
            self._machine_id = h.hexdigest()[:32]


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

    @property
    def workspace_dir(self) -> str:
        return self._workspace_dir

    @property
    def job_log_dir(self) -> str:
        return self._job_log_dir

    @property
    def supported_architectures(self) -> List[str]:
        return self._architectures

    @property
    def dput_host(self) -> str:
        return self._dput_host

    @property
    def gpg_key_uid(self) -> str:
        return self._gpg_key_uid
