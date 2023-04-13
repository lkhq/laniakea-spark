# -*- coding: utf-8 -*-
#
# Copyright (C) 2017-2020 Matthias Klumpp <matthias@tenstral.net>
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
import json
import logging as log
from enum import StrEnum

import zmq
import zmq.auth

from spark.utils.misc import to_compact_json


class JobStatus(StrEnum):
    """Returned status ob a Job"""

    ACCEPTED = 'accepted'  # worker accepted the job
    REJECTED = 'rejected'  # worker rejected taking the job
    SUCCESS = 'success'  # success
    FAILED = 'failed'  # job failed
    DEPWAIT = 'depwait'  # waits for a dependency


class ReplyException(Exception):
    pass


class MessageException(Exception):
    pass


class ServerErrorException(Exception):
    pass


# maximum amount of time to wait for a server response
RESPONSE_WAIT_TIME = 15000  # 15sec


class ServerConnection:
    def __init__(self, conf, ctx):
        if zmq.zmq_version_info() < (4, 0):
            raise RuntimeError(
                "Security is not supported in libzmq version < 4.0. libzmq version {0}".format(
                    zmq.zmq_version()
                )
            )
        self._conf = conf
        self._zctx = ctx

        self._send_attempts = 0

    def connect(self):
        """
        Set up an encrypted connection to the Lighthouse server
        andf run it.
        """

        # construct base data to include in all requests to the server
        self._base_req = {}
        self._base_req['machine_name'] = self._conf.machine_name
        self._base_req['machine_id'] = self._conf.client_uuid

        # initialize Lighthouse socket
        self._sock = self._zctx.socket(zmq.REQ)
        self._sock.setsockopt(zmq.REQ_RELAXED, 1)

        # set server certificate
        server_public, _ = zmq.auth.load_certificate(self._conf.server_cert_fname)
        self._sock.curve_serverkey = server_public

        # set client certificate
        client_secret_file = os.path.join(self._conf.client_cert_fname)
        client_public, client_secret = zmq.auth.load_certificate(client_secret_file)
        self._sock.curve_secretkey = client_secret
        self._sock.curve_publickey = client_public

        # connect
        self._sock.connect(self._conf.lighthouse_server)

        self._poller = zmq.Poller()
        self._poller.register(self._sock, zmq.POLLIN)

    def reconnect(self):
        """
        Re-establish connection. The lazy answer in case we got
        no reply from the server for a while.
        """
        self._sock.close()
        self.connect()

    def send_job_status(self, job_id, status):
        req = self.new_base_request()

        req['request'] = 'job-{}'.format(status)
        req['uuid'] = job_id

        try:
            self._sock.send_string(to_compact_json(req))
        except zmq.error.ZMQError as e:
            self._send_attempt_failed(e)
            log.error('ZMQ error while sending job status: %s', str(e))
        try:
            sockev = dict(self._poller.poll(RESPONSE_WAIT_TIME))
        except zmq.error.ZMQError as e:
            self._send_attempt_failed()
            log.error('ZMQ error while waiting for reply: %s', str(e))
        if sockev.get(self._sock) == zmq.POLLIN:
            self._sock.recv_multipart()  # discard reply
        else:
            log.error('Unable to send job status: No reply from master')

    def new_base_request(self):
        """
        Get a copy of the base request template.
        """
        return dict(self._base_req)

    def request_job(self):
        """
        Request a new job from the server.
        """

        # construct job request
        req = dict(self._base_req)
        req['request'] = 'job'
        req['accepts'] = self._conf.accepted_job_kinds
        req['architectures'] = self._conf.supported_architectures

        # request job
        self._sock.send_string(to_compact_json(req))

        # wait for a reply
        job_reply_msgs = None
        try:
            sockev = dict(self._poller.poll(RESPONSE_WAIT_TIME))
        except zmq.error.ZMQError as e:
            self._send_attempt_failed()
            raise ReplyException('ZMQ error while polling for reply: ' + str(e)) from e

        if sockev.get(self._sock) == zmq.POLLIN:
            job_reply_msgs = self._sock.recv_multipart()
        else:
            self._send_attempt_failed()
            raise ReplyException('Job request expired (the master server might be unreachable).')

        if not job_reply_msgs:
            raise ReplyException('Invalid server response on a job request.')
        job_reply_raw = job_reply_msgs[0]

        job_reply = None
        try:
            job_reply = json.loads(str(job_reply_raw, 'utf-8'))
        except Exception as e:
            raise MessageException(
                'Unable to decode server reply ({0}): {1}'.format(job_reply_raw, str(e))
            ) from e
        if not job_reply:
            log.debug('No new jobs.')
            return None

        try:
            server_error = job_reply.get('error')
        except Exception as e:
            raise ServerErrorException(
                'Received unexpected server reply: {}'.format(str(job_reply))
            ) from e

        if server_error:
            raise ServerErrorException(
                'Received error message from server: {}'.format(server_error)
            )

        return job_reply

    def _send_attempt_failed(self, error=None):
        self._send_attempts = self._send_attempts + 1
        if self._send_attempts >= 6:
            if error:
                log.error('Send attempts expired ({}), reconnecting...'.format(str(error)))
            else:
                log.error('Send attempts expired, reconnecting...')
            self.reconnect()
            self._send_attempts = 0

    def send_str_noreply(self, s):
        if type(s) is str:
            data = s.encode('utf-8')
        elif type(s) is not bytes:
            data = str(s).encode('utf-8')

        self._sock.send(data, copy=False, track=True)
        try:
            sockev = dict(self._poller.poll(RESPONSE_WAIT_TIME))
        except zmq.error.ZMQError as e:
            self._send_attempt_failed(e)

        if sockev.get(self._sock) == zmq.POLLIN:
            self._sock.recv_multipart()  # discard reply
        else:
            self._send_attempt_failed()
            log.info('Received no ACK from server for noreply request.')
