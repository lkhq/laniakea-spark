# Copyright (C) 2016-2017 Matthias Klumpp <matthias@tenstral.net>
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
from multiprocessing import Process
import zmq

from spark.config import LocalConfig
from spark.connection import ServerConnection
from spark.worker import Worker

class Daemon:

    def __init__(self, log_level=None):
        if not log_level:
            log_level = log.INFO
        log.basicConfig(level=log_level, format="[%(levelname)s] %(message)s")


    '''
    Set up connection for a new worker process and launch it.
    This function is executed in a new process.
    '''
    def run_worker_process(self, worker_name):
        zctx = zmq.Context()

        # initialize Lighthouse connection
        conn = ServerConnection(self._conf, zctx)

        # connect
        conn.connect()
        log.info('Running {0} on {1} ({2})'.format(worker_name, self._conf.machine_name, self._conf.machine_id))

        w = Worker(self._conf, conn)
        w.run()


    def run(self):
        self._conf = LocalConfig()
        self._conf.load()

        log.info('Maximum number of parallel jobs: {0}'.format(self._conf.max_jobs))

        # initialize workers
        self._workers = []
        for i in range(0, self._conf.max_jobs):
            worker_name = 'worker_{}'.format(i)
            p = Process(target=self.run_worker_process, args=(worker_name,))
            p.name = worker_name
            p.start()
            self._workers.append(p)
