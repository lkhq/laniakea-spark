# -*- coding: utf-8 -*-
#
# Copyright (C) 2016-2020 Matthias Klumpp <matthias@tenstral.net>
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

import sys
import shutil
import logging as log
from multiprocessing import Process

import zmq

from spark.config import LocalConfig
from spark.worker import Worker
from spark.connection import ServerConnection


class Daemon:
    def __init__(self, log_level=None):
        if not log_level:
            log_level = log.INFO
        log.basicConfig(level=log_level, format="[%(levelname)s] %(message)s")

    def run_worker_process(self, worker_name):
        """
        Set up connection for a new worker process and launch it.
        This function is executed in a new process.
        """

        zctx = zmq.Context()

        # initialize Lighthouse connection
        conn = ServerConnection(self._conf, zctx)

        # connect
        conn.connect()
        log.info(
            'Running {0} on {1} ({2})'.format(
                worker_name, self._conf.machine_name, self._conf.client_uuid
            )
        )

        w = Worker(self._conf, conn)
        w.run()

    def run(self):
        # check Python platform version - 3.5 works while 3.6 or higher is properly tested
        pyversion = sys.version_info
        if pyversion < (3, 5):
            raise Exception(
                'Laniakea-Spark needs Python >= 3.5 to work. Please upgrade your Python version.'
            )
        if pyversion >= (3, 5) and pyversion < (3, 6):
            log.info('Running on Python 3.5 while Python 3.6 is recommended.')
        if not shutil.which('debspawn'):
            log.warning(
                'The "debspawn" tool was not found in PATH, we will not be able to run most actions.'
            )

        self._conf = LocalConfig()
        self._conf.load()

        log.info('Maximum number of parallel jobs: {0}'.format(self._conf.max_jobs))

        # initialize workers
        if self._conf.max_jobs == 1:
            # don't use multiprocess when our maximum amount of jobs is just 1
            self.run_worker_process('worker_0')
        else:
            for i in range(0, self._conf.max_jobs):
                worker_name = 'worker_{}'.format(i)
                p = Process(target=self.run_worker_process, args=(worker_name,))
                p.name = worker_name
                p.start()
