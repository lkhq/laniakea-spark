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

from io import StringIO
from contextlib import contextmanager
import threading
from spark.utils.misc import to_compact_json


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

        self._msg_template = self._conn.new_base_request()
        self._msg_template['request'] = 'job-status'
        self._msg_template['uuid']    = str(job_id)

        self._have_output = False
        self._closed = False
        self._send_timed()  # start timer

    def write(self, s):
        if isinstance(s, (bytes, bytearray)):
            s = str(s, 'utf-8')
        self._buf.write(s)
        self._file.write(s)
        self._have_output = True

    def flush(self):
        self._file.flush()

    def _send_timed(self):
        if self._have_output:
            self._send_buffer(self._last_msg_excerpt)
        if not self._closed:
            threading.Timer(20.0, self._send_timed).start()

    def _send_buffer(self, prefix=None):
        if not self._have_output:
            return
        self._have_output = False
        log_excerpt = self._buf.getvalue()
        self._buf = StringIO()

        if prefix:
            log_excerpt = prefix + log_excerpt

        req = dict(self._msg_template)  # copy the template
        req['log_excerpt'] = log_excerpt

        self._conn.send_str_noreply(to_compact_json(req))
        self._last_msg_excerpt = log_excerpt

    def close(self):
        self._closed = True
        self._file.close()

    @property
    def job_id(self) -> str:
        return self._job_id


@contextmanager
def job_log(lhconn, job_id, log_fname):
    jlog = JobLog(lhconn, job_id, log_fname)
    try:
        yield jlog
    finally:
        jlog.close()
