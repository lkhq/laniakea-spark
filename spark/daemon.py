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

import os
import sys
import asyncio
import logging as log
import json

import zmq
import zmq.auth
from zmq.auth.asyncio import AsyncioAuthenticator
from zmq.asyncio import Context, ZMQEventLoop, Poller

from spark.config import LocalConfig
from spark.worker import Worker

class Daemon:

    def __init__(self, log_level=None):
        if not log_level:
            log_level = log.INFO
        log.basicConfig(level=log_level, format="[%(levelname)s] %(message)s")


    def _construct_job_request_message(self):
        req = {}

        req['request'] = 'job'
        req['machine_name'] = self._conf.machine_name
        req['machine_id'] = self._conf.machine_id
        req['accepts'] = ['*']
        req['architectures'] = ['*']

        return str(json.dumps(req))


    '''
    Request a new job if we have free workers.
    '''
    async def _request_jobs(self):
        for worker in self._workers:
            if worker.running:
                continue

            poller = Poller()
            poller.register(self._lhsock, zmq.POLLIN)
            self._lhsock.send_string(self._construct_job_request_message())

            # wait 5sec for a reply
            if (poller.poll(5000)):
                msg = self._lhsock.recv()
                log.info(str(msg, 'utf-8'))
            else:
                log.error('Job request expired (the master server might be unreachable).')

            worker.start("test")


    async def _request_jobs_periodic(self):
        while True:
            await self._request_jobs()
            await asyncio.sleep(20) # wait 20s before checking for new jobs again


    def run(self):
        if zmq.zmq_version_info() < (4,0):
            raise RuntimeError("Security is not supported in libzmq version < 4.0. libzmq version {0}".format(zmq.zmq_version()))

        self._conf = LocalConfig()
        self._conf.load()

        # FIXME: We use a sync context here, as otherwise any polling
        # runs us into a "ValueError: Invalid file object: <zmq.asyncio.Socket object at 0x7f434f67f9a8>" error.
        self._zctx = zmq.Context()

        # initialize Lighthouse proxy
        self._lhsock = self._zctx.socket(zmq.DEALER)

        # set server certificate
        server_public, _ = zmq.auth.load_certificate(self._conf.server_cert_fname)
        self._lhsock.curve_serverkey = server_public

        # set client certificate
        client_secret_file = os.path.join(self._conf.client_cert_fname)
        client_public, client_secret = zmq.auth.load_certificate(client_secret_file)
        self._lhsock.curve_secretkey = client_secret
        self._lhsock.curve_publickey = client_public

        # connect
        self._lhsock.connect(self._conf.lighthouse_server)
        log.info('Running on {0} ({1}), job capacity: {2}'.format(self._conf.machine_name, self._conf.machine_id, self._conf.max_jobs))

        # initialize the right amount of workers
        # workers will use almost no resources when idle
        self._workers = []
        for i in range(0, self._conf.max_jobs):
            self._workers.append(Worker())

        # proxy the encrypted connection so worker threads can
        # use it easily.
        print("A")

        backendsock = self._zctx.socket(zmq.DEALER)
        backendsock.bind('inproc://backend')
        zmq.proxy(self._lhsock, backendsock)
        print("B")

        # run the event loop
        loop = ZMQEventLoop()
        asyncio.set_event_loop(loop)
        asyncio.Task(self._request_jobs_periodic())
        loop.run_forever()
        loop.close()
        self._lhsock.close()
