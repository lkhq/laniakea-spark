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
import zmq.auth

from spark.config import LocalConfig
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

        # initialize Lighthouse socket
        lhsock = zctx.socket(zmq.DEALER)

        # set server certificate
        server_public, _ = zmq.auth.load_certificate(self._conf.server_cert_fname)
        lhsock.curve_serverkey = server_public

        # set client certificate
        client_secret_file = os.path.join(self._conf.client_cert_fname)
        client_public, client_secret = zmq.auth.load_certificate(client_secret_file)
        lhsock.curve_secretkey = client_secret
        lhsock.curve_publickey = client_public

        # connect
        lhsock.connect(self._conf.lighthouse_server)
        log.info('Running {0} on {1} ({2})'.format(worker_name, self._conf.machine_name, self._conf.machine_id))

        w = Worker(self._conf, lhsock)
        w.run()


    def run(self):
        if zmq.zmq_version_info() < (4,0):
            raise RuntimeError("Security is not supported in libzmq version < 4.0. libzmq version {0}".format(zmq.zmq_version()))

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
