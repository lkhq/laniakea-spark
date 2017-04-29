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
import json
import zmq
import zmq.auth
import logging as log


class JobStatus:
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'


class ReplyException(Exception):
    pass


class MessageException(Exception):
    pass


class ServerErrorException(Exception):
    pass


class ServerConnection:

    def __init__(self, conf, ctx):
        if zmq.zmq_version_info() < (4, 0):
            raise RuntimeError("Security is not supported in libzmq version < 4.0. libzmq version {0}".format(zmq.zmq_version()))
        self._conf = conf
        self._zctx = ctx

        self._send_attempts = 0

    '''
    Set up an encrypted connection to the Lighthouse server
    andf run it.
    '''
    def connect(self):

        # construct base data to include in all requests to the server
        self._base_req = {}
        self._base_req['machine_name'] = self._conf.machine_name
        self._base_req['machine_id'] = self._conf.machine_id

        # initialize Lighthouse socket
        self._sock = self._zctx.socket(zmq.DEALER)

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


    '''
    Re-establish connection. The lazy answer in case we got
    no reply from the server for a while.
    '''
    def reconnect(self):
        self._sock.close()
        self.connect()


    def send_job_request_status(self, job_id, status):
        req = self.new_base_request()

        req['request'] = 'job-{}'.format(status)
        req['_id'] = job_id

        self._sock.send_string(str(json.dumps(req)))
        try:
            self._sock.poll(4)
        except:
            self.__send_attempt_failed()


    '''
    Get a copy of the base request template.
    '''
    def new_base_request(self):
        return dict(self._base_req)


    '''
    Request a new job from the server.
    '''
    def request_job(self):
        poller = zmq.Poller()
        poller.register(self._sock, zmq.POLLIN)


        # construct job request
        req = dict(self._base_req)
        req['request'] = 'job'
        req['accepts'] = ['*']
        req['architectures'] = ['*']

        # request job
        self._sock.send_string(str(json.dumps(req)))

        # wait 5sec for a reply
        job_reply_raw = None
        if (poller.poll(5000)):
            job_reply_raw = self._sock.recv()
        else:
            self._send_attempt_failed()
            raise ReplyException('Job request expired (the master server might be unreachable).')

        job_reply = None
        try:
            job_reply = json.loads(str(job_reply_raw, 'utf-8'))
        except Exception as e:
            raise MessageException('Unable to decode server reply ({0}): {1}'.format(job_reply_raw, str(e)))
        if not job_reply:
            log.debug('No new jobs.')
            return None

        server_error = job_reply.get('error')
        if server_error:
            raise ServerErrorException('Received error message from server: {}'.format(server_error))

        return job_reply


    def _send_attempt_failed(self):
        self._send_attempts = self._send_attempts + 1
        if self._send_attempts >= 8:
            log.error('Send attempts expired, reconnecting...')
            self.reconnect()
            self._send_attempts = 0


    def send_str_noreply(self, s):
        mt = self._sock.send(str(s).encode('utf-8'), copy=False, track=True)
        try:
            mt.wait(4) # wait for 4 seconds for the mesage to be sent
        except:
            self._send_attempt_failed()