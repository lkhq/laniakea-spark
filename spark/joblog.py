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
from io import StringIO


'''
Send status information (usually in form of stdout/stderr output)
for a specific job to the server as well as to the local config file.
'''
class JobLog:

    def __init__(self, lhconn, job_id):
        self._conn = lhconn
        self._buf = StringIO()

        self._msg_template = self._conn.new_base_request()
        self._msg_template['request'] = 'job-status'
        self._msg_template['_id']     = str(job_id)


    def write(self, s):
        r = self._buf.write(s)
        self._buf.seek(0, os.SEEK_END)
        if self._buf.tell() >= 2 * 1024:
            self._send_buffer()
        return r


    def flush(self):
        self._send_buffer()


    def _send_buffer(self):
        log_excerpt = self._buf.getvalue()
        self._buf = StringIO()

        req = dict(self._msg_template) # copy the template
        req['log_excerpt'] = log_excerpt

        self._conn.send_str_noreply(str(json.dumps(req)))