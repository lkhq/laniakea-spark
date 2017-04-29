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
import sys
import asyncio
import logging as log
import json
import time
import zmq

from spark.statusproxy import StatusProxy


class JobStatus:
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'


class Worker:

    def __init__(self, conf, lighthouse_socket):
        self._lhsock = lighthouse_socket
        self._conf = conf


    def _base_request_data(self):
        req = {}
        req['machine_name'] = self._conf.machine_name
        req['machine_id'] = self._conf.machine_id

        return req


    def _construct_job_request_message(self):
        req = self._base_request_data()

        req['request'] = 'job'
        req['accepts'] = ['*']
        req['architectures'] = ['*']

        return str(json.dumps(req))


    def _send_job_status(self, job_id, status):
        req = self._base_request_data()

        req['request'] = 'job-{}'.format(status)
        req['_id'] = job_id

        self._lhsock.send_string(str(json.dumps(req)))


    def _run_job(self, runner, job):
        job_id = job.get('_id')
        workspace = os.path.join(self._conf.workspace, job_id)

        if not runner.set_job(job, workspace):
            self._send_job_status(job_id, JobStatus.REJECTED)
            return
        self._send_job_status(job_id, JobStatus.ACCEPTED)

        log.info('Running job \'{}\''.format(job_id))
        runner.run()


    '''
    Request a new job.
    '''
    def _request_job(self):
        poller = zmq.Poller()
        poller.register(self._lhsock, zmq.POLLIN)
        self._lhsock.send_string(self._construct_job_request_message())

        # wait 5sec for a reply
        job_reply_raw = None
        if (poller.poll(5000)):
            job_reply_raw = self._lhsock.recv()
        else:
            log.error('Job request expired (the master server might be unreachable).')
            return

        job_reply = None
        try:
            job_reply = json.loads(str(job_reply_raw, 'utf-8'))
        except Exception as e:
            log.error('Unable to decode server reply: {}'.format(str(e)))
            return
        if not job_reply:
            log.debug('No new jobs.')
            return

        server_error = job_reply.get('error')
        if server_error:
            log.warning('Received error message from server: {}'.format(server_error))
            return

        job_module = job_reply.get('module')
        job_kind   = job_reply.get('kind')
        job_id     = job_reply.get('_id')

        proxy = StatusProxy(self._lhsock, self._conf.machine_name, self._conf._machine_id, job_id)
        if job_module == 'isotope' and job_kind == 'image-build':
            from spark.runners.iso_build import IsoBuilder
            return self._run_job(IsoBuilder(proxy), job_reply)
        else:
            log.warning('Received job of type {0}::{1} which we can not handle.'.format(job_module, job_kind))
            self._send_job_status(job_id, JobStatus.REJECTED)
        log.info(job_reply)


    def run(self):
        while True:
            self._request_job()
            time.sleep(20) # wait 20s before trying again
