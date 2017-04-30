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

import json
from io import StringIO
from contextlib import contextmanager


class JobLog:
    """
    Send status information (usually in form of stdout/stderr output)
    for a specific job to the server as well as to the local config file.
    """

    def __init__(self, lhconn, job_id, log_fname):
        self._conn = lhconn
        self._buf = StringIO()
        self._file = open(log_fname, 'w')
        self._last_msg_excerpt = ''
        self._job_id = job_id
        self._buf_len = 0

        self._msg_template = self._conn.new_base_request()
        self._msg_template['request'] = 'job-status'
        self._msg_template['_id']     = str(job_id)


    def write(self, s):
        if isinstance(s, (bytes, bytearray)):
            s = str(s, 'utf-8')
        self._buf_len = self._buf.write(s) + self._buf_len
        self._file.write(s)

        if self._buf_len >= 2 * 256:
            self._send_buffer()


    def flush(self):
        self._send_buffer(self._last_msg_excerpt)
        self._file.flush()


    def _send_buffer(self, prefix=None):
        log_excerpt = self._buf.getvalue()
        self._buf = StringIO()

        if prefix:
            log_excerpt = prefix + log_excerpt

        req = dict(self._msg_template) # copy the template
        req['log_excerpt'] = log_excerpt

        self._conn.send_str_noreply(str(json.dumps(req)))
        self._last_msg_excerpt = log_excerpt
        self._buf_len = 0


    def close(self):
        self.flush()
        self._file.close()


    @property
    def job_id(self) -> str:
        return self._job_id


@contextmanager
def joblog(lhconn, job_id, log_fname):
    jlog = JobLog(lhconn, job_id, log_fname)
    try:
        yield jlog
    finally:
        jlog.close()
