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
import logging as log
import zmq
import json
from io import StringIO


'''
Send status information (usually in form of stdout/stderr outout)
for a specific job to the server.
'''
class StatusProxy:

    def __init__(self, socket, machine_name, machine_id, job_id):
        self._sock = socket
        self._buf = StringIO()

        self._msg_template = {}
        self._msg_template['request'] = 'job-status'
        self._msg_template['_id']     = str(job_id)
        self._msg_template['machine_name'] = str(machine_name)
        self._msg_template['machine_id']   = str(machine_id)

    def write(self, s):
        r = self._buf.write(s)
        self._buf.seek(0, os.SEEK_END)
        if self._buf.tell() >= 4 * 1024:
            self._send_buffer()
        return r

    def _send_buffer(self):
        log_excerpt = self._buf.getvalue()
        self._buf = StringIO()

        req = dict(self._msg_template) # copy the template
        req['log_excerpt'] = log_excerpt

        self._sock.send_json(req)
