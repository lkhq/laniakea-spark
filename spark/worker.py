# -*- coding: utf-8 -*-
#
# Copyright (C) 2017-2018 Matthias Klumpp <matthias@tenstral.net>
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
import shutil
from email.utils import formatdate

from spark.connection import JobStatus, ServerErrorException
from spark.joblog import job_log
from spark.runners import load_module, PLUGINS


class Worker:
    '''
    One task runner, executing the actual job by doing some housekeeping and
    calling the appropriate runner.
    '''

    def __init__(self, conf, lighthouse_connection):
        self._conn = lighthouse_connection
        self._conf = conf


    def _run_job(self, job):
        from spark.utils.schroot import lkworkspace
        from spark.utils.deb822 import Changes
        from spark.utils.misc import cd, upload

        # basic job information
        job_id = job.get('uuid')
        job_arch = job.get('architecture')
        if not job_arch:
            job_arch = 'all'

        # job workspace directories
        workspace = os.path.join(self._conf.workspace_dir, job_id)
        artifacts_dir = os.path.join(workspace, 'artifacts')

        # set up default workspace directories
        if not os.path.exists(artifacts_dir):
            os.makedirs(artifacts_dir)
        if not os.path.exists(self._conf.job_log_dir):
            os.makedirs(self._conf.job_log_dir)

        # set the logfile and run the job
        log.info('Running job \'{}\''.format(job_id))
        log_fname = os.path.join(self._conf.job_log_dir, '{}.log'.format(job_id))
        success = False

        runner_name = job['kind']
        if not PLUGINS.get(runner_name):
            self._conn.send_job_status(job_id, JobStatus.REJECTED)
            log.info('Forwarded job \'{}\' - no runner for kind "{}"'.format(job_id, job['kind']))
            return

        self._conn.send_job_status(job_id, JobStatus.ACCEPTED)

        run, version = load_module(runner_name)
        with lkworkspace(workspace):
            with job_log(self._conn, job_id, log_fname) as jlog:
                try:
                    success, files, changes = run(jlog, job, job.get('data'))
                except:
                    import traceback
                    tb = traceback.format_exc()
                    jlog.write(tb)
                    self._conn.send_job_status(job_id, JobStatus.REJECTED)
                    log.warning(tb)
                    log.info('Rejected job {}'.format(job_id))
                    return

            # logfile is closed here
            if not files:
                files = list()

            # create directory with files to upload
            if not os.path.exists(artifacts_dir):
                os.makedirs(artifacts_dir)

            with cd(artifacts_dir):
                # write upload description file
                # (upload additional artifacts which the runner hasn't dealt with,
                # including the final logfile)
                dud = Changes()
                dud['Format'] = '1.8'
                dud['Date'] = formatdate()
                dud['Architecture'] = job_arch
                dud['X-Spark-Job'] = str(job_id)
                dud['X-Spark-Success'] = 'Yes' if success else 'No'

                # collect list of additional files to upload
                files.append(log_fname)
                for f in files:
                    shutil.copyfile(f, os.path.basename(f))
                    dud.add_file(os.path.basename(f))

                dudf = "{}.dud".format(job_id)
                with open(dudf, 'wb') as fd:
                    dud.dump(fd=fd)

                # send the result to the remote server
                try:
                    if changes:
                        upload(changes, self._conf.gpg_key_uid, self._conf.dput_host)
                    upload(dudf, self._conf.gpg_key_uid, self._conf.dput_host)
                except Exception as e:
                    import sys
                    print(e, file=sys.stderr)
                    success = False

        jstatus = JobStatus.FAILED
        if success:
            jstatus = JobStatus.SUCCESS

        self._conn.send_job_status(job_id, jstatus)
        log.info('Finished job {0}, {1}'.format(job_id, str(jstatus)))


    def _request_job(self):
        """
        Request a new job.
        """

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
            return False

        job_module = job_reply.get('module')
        job_kind   = job_reply.get('kind')
        job_id     = job_reply.get('uuid')

        if job_kind in self._conf.accepted_job_kinds:
            return self._run_job(job_reply)
        else:
            log.warning('Received job of type {0}::{1} which we can not handle.'.format(job_module, job_kind))
            self._conn.send_job_status(job_id, JobStatus.REJECTED)
            return False


    def run(self):
        while True:
            if not self._request_job():
                time.sleep(30) # wait 30s before trying again
