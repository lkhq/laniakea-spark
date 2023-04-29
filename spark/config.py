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
import sys
import logging as log
import platform
from typing import List
from pathlib import Path

import tomlkit


class ConfigError(Exception):
    """Some problem in the configuration was found."""


class LocalConfig:
    """
    Local configuration for the spark daemon.
    """

    CERTS_BASE_DIR = '/etc/laniakea/keys/curve/'

    def load(self, fname=None):
        if not fname:
            fname = '/etc/laniakea/spark.toml'

        cdata = None
        with open(fname, encoding='utf8') as toml_file:
            try:
                cdata = tomlkit.load(toml_file)
            except tomlkit.exceptions.ParseError as e:
                print(
                    'Unable to parse configuration ({}): {}'.format(fname, str(e)),
                    file=sys.stderr,
                )
                sys.exit(6)

        self._machine_name = cdata.get('MachineName')
        if not self._machine_name:
            self._machine_name = (
                Path('/etc/hostname').read_text(encoding='utf-8').strip('\n').strip()
            )

        # read the machine ID
        self._machine_id = Path('/etc/machine-id').read_text(encoding='utf-8').strip('\n').strip()

        # make an UUID for this client from the machine name
        self._make_client_uuid(self._machine_name)

        self._lighthouse_server = cdata.get('LighthouseServer')
        if not self._lighthouse_server:
            raise ConfigError(
                'The "LighthouseServer" configuration entry is missing. '
                'Please specify the address of a Lighthouse server.'
            )

        self._max_jobs = int(cdata.get("MaxJobs", 1))
        if self._max_jobs < 1:
            raise ConfigError('The maximum number of jobs can not be < 1.')

        self._client_cert_fname = os.path.join(
            self.CERTS_BASE_DIR, 'secret', '{0}-spark_private.sec'.format(self.machine_name)
        )
        self._server_cert_fname = os.path.join(
            self.CERTS_BASE_DIR, '{0}_lighthouse-server.pub'.format(self.machine_name)
        )

        workspace_root = cdata.get('WorkspaceRoot')
        if not workspace_root:
            workspace_root = '/var/lib/lkspark/'
        self._workspace_dir = os.path.join(workspace_root, 'workspaces')
        self._job_log_dir = os.path.join(workspace_root, 'logs')
        self._dput_cf_fname = os.path.join(workspace_root, 'dput.cf')

        self._architectures = cdata.get("Architectures")
        if not self._architectures:
            import re

            # try to rescue doing some poor mapping to the Debian arch vendor strings
            # for a couple of common architectures
            machine_str = platform.machine()
            if machine_str == 'x86_64':
                self._architectures = ['amd64']
            elif re.match('i?86', machine_str):
                self._architectures = ['i386']
            elif machine_str == 'aarch64':
                self._architectures = ['arm64']
            else:
                self._architectures = [machine_str]
                log.warning('Using auto-detected architecture name: {}'.format(machine_str))

        self._accepted_job_kinds = cdata.get("AcceptedJobs")
        if not self._accepted_job_kinds:
            raise ConfigError(
                'The essential "AcceptedJobs" configuration entry is missing - '
                'without accepting any job type, running this daemon is pointless.'
            )

        self._gpg_key_id = cdata.get('GpgKeyID')
        if not self._gpg_key_id:
            raise ConfigError('The essential "GpgKeyID" configuration entry is missing.')

    def _make_client_uuid(self, machine_name):
        import uuid

        client_uuid = uuid.uuid5(uuid.UUID('d44a99a2-0b5d-415b-808a-790ad4684309'), machine_name)
        self._client_uuid = str(client_uuid)

    @property
    def machine_id(self) -> str:
        return self._machine_id

    @property
    def client_uuid(self) -> str:
        return self._client_uuid

    @property
    def machine_name(self) -> str:
        return self._machine_name

    @property
    def accepted_job_kinds(self) -> List[str]:
        return self._accepted_job_kinds

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
    def dput_cf_fname(self) -> str:
        """Path to our dput.cf filename."""
        return self._dput_cf_fname

    @property
    def job_log_dir(self) -> str:
        return self._job_log_dir

    @property
    def supported_architectures(self) -> List[str]:
        return self._architectures

    @property
    def gpg_key_id(self) -> str:
        return self._gpg_key_id
