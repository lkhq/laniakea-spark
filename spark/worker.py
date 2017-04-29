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
import logging as log
import time

from spark.connection import *
from spark.joblog import JobLog


class Worker:

    def __init__(self, conf, lighthouse_connection):
        self._conn = lighthouse_connection
        self._conf = conf


    def _run_job(self, runner, jlog, job):
        job_id = job.get('_id')
        workspace = os.path.join(self._conf.workspace, job_id)

        if not runner.set_job(job, workspace):
            self._conn.send_job_request_status(job_id, JobStatus.REJECTED)
            return
        self._conn.send_job_request_status(job_id, JobStatus.ACCEPTED)

        log.info('Running job \'{}\''.format(job_id))
        try:
            runner.run()
        except:
            import traceback
            tb = traceback.format_exc()
            jlog.write(tb)
            jlog.flush()
            self._conn.send_job_request_status(job_id, JobStatus.REJECTED)


    '''
    Request a new job.
    '''
    def _request_job(self):

        job_reply = None
        try:
            job_reply = self._conn.request_job()
        except ServerErrorException as e:
            log.warning(str(e))
            return
        except Exception as e:
            log.error(str(e))
            return

        if not job_reply:
            # there are no jobs available for us
            return

        job_module = job_reply.get('module')
        job_kind   = job_reply.get('kind')
        job_id     = job_reply.get('_id')

        jlog = JobLog(self._conn, job_id)
        if job_module == 'isotope' and job_kind == 'image-build':
            from spark.runners.iso_build import IsoBuilder
            return self._run_job(IsoBuilder(jlog), jlog, job_reply)
        else:
            log.warning('Received job of type {0}::{1} which we can not handle.'.format(job_module, job_kind))
            self._conn.send_job_request_status(job_id, JobStatus.REJECTED)
        log.info(job_reply)


    def run(self):
        while True:
            self._request_job()
            time.sleep(20) # wait 20s before trying again
