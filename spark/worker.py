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
import time
import shutil
import logging as log
from email.utils import formatdate

from spark.utils import RunnerResult
from spark.config import LocalConfig
from spark.joblog import job_log
from spark.runners import PLUGINS, load_module
from spark.connection import JobStatus, ServerErrorException


class Worker:
    """
    A task supervisor, executing the actual job by doing some housekeeping and
    calling the appropriate runner.
    """

    def __init__(self, conf: LocalConfig, lighthouse_connection, is_primary: bool = True):
        self._conn = lighthouse_connection
        self._conf = conf
        self._is_primary = is_primary

    def _run_job(self, job):
        '''
        Run a job. Return True if the job was handled in some
        way and we did not reject it again.
        '''

        from spark.utils.misc import cd, upload
        from spark.utils.deb822 import Changes
        from spark.utils.workspace import lkworkspace

        # basic job information
        job_id = job.get('uuid')
        job_arch = job.get('architecture')
        if not job_arch:
            job_arch = 'all'

        # job workspace directories
        workspace = os.path.join(self._conf.workspace_dir, job_id)
        artifacts_dir = os.path.join(workspace, 'artifacts')

        # set up default workspace directories
        try:
            if not os.path.exists(artifacts_dir):
                os.makedirs(artifacts_dir)
            if not os.path.exists(self._conf.job_log_dir):
                os.makedirs(self._conf.job_log_dir)
        except OSError as e:
            self._conn.send_job_status(job_id, JobStatus.REJECTED)
            log.error(
                'Failed to create working directory for \'{}\': {} (job forwarded)'.format(
                    job_id, str(e)
                )
            )
            try:
                shutil.rmtree(workspace)
            except Exception:
                pass  # we failed to create the workspace, so failing to clean it up is not an error
            return False

        # set the logfile and run the job
        log.info('Running job \'%s\'', job_id)
        log_fname = os.path.join(self._conf.job_log_dir, '{}.log'.format(job_id))

        runner_name = job['kind']
        job_repo = job.get('repo')
        if not job_repo:
            self._conn.send_job_status(job_id, JobStatus.REJECTED)
            log.info(
                'Forwarded job \'%s\' - no repository set to upload generated artifacts to.', job_id
            )
            return False

        if not PLUGINS.get(runner_name):
            self._conn.send_job_status(job_id, JobStatus.REJECTED)
            log.info('Forwarded job \'%s\' - no runner for kind "%s"', job_id, job['kind'])
            return False

        self._conn.send_job_status(job_id, JobStatus.ACCEPTED)

        run, _ = load_module(runner_name)
        with lkworkspace(workspace):
            with job_log(self._conn, job_id, log_fname) as jlog:
                try:
                    build_result, files, changes = run(jlog, job, job.get('data'))
                except:  # noqa: E722 pylint: disable=bare-except
                    import traceback

                    tb = traceback.format_exc()
                    jlog.write(tb)
                    self._conn.send_job_status(job_id, JobStatus.REJECTED)
                    log.warning(tb)
                    log.info('Rejected job {}'.format(job_id))
                    return False

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
                dud['X-Spark-Result'] = str(build_result)

                # collect list of additional files to upload
                files.append(log_fname)
                for f in files:
                    fbase = os.path.basename(f)
                    if not os.path.isfile(fbase):
                        shutil.copyfile(f, fbase)
                    dud.add_file(fbase)

                dudf = "{}.dud".format(job_id)
                with open(dudf, 'wb') as fd:
                    dud.dump(fd=fd)

                # send the result to the remote server
                try:
                    if changes:
                        upload(changes, self._conf.gpg_key_id, job_repo, self._conf._dput_cf_fname)
                    upload(dudf, self._conf.gpg_key_id, job_repo, self._conf._dput_cf_fname)
                except Exception as e:
                    import sys

                    print(e, file=sys.stderr)

        jstatus = JobStatus.FAILED
        if build_result == RunnerResult.SUCCESS:
            jstatus = JobStatus.SUCCESS

        self._conn.send_job_status(job_id, jstatus)
        log.info('Finished job {0}, {1}'.format(job_id, str(jstatus)))

        return True

    def _request_job(self):
        """
        Request a new job.
        """

        job_reply = None
        try:
            job_reply = self._conn.request_job()
        except ServerErrorException as e:
            log.warning(str(e))
            return False
        except Exception as e:
            log.error('Error when requesting job: {}'.format(str(e)))
            return False

        if not job_reply:
            # there are no jobs available for us
            return False

        # Now that we've accepted a job, we just reply to the server, even if
        # an exception occurs.  If we don't, the job is stuck indefinitely and
        # we will not be able to accept another.
        try:
            job_module = job_reply.get('module')
            job_kind = job_reply.get('kind')
            job_id = job_reply.get('uuid')

            if job_kind in self._conf.accepted_job_kinds:
                return self._run_job(job_reply)
            else:
                log.warning(
                    'Received job of type {0}::{1} which we can not handle.'.format(
                        job_module, job_kind
                    )
                )
                self._conn.send_job_status(job_id, JobStatus.REJECTED)
                return False
        except:  # noqa: E722 pylint: disable=bare-except
            import traceback

            tb = traceback.format_exc()
            log.info(tb)
            self._conn.send_job_status(job_id, JobStatus.REJECTED)
            log.warning(tb)
            log.info('Rejected job {} due to exception'.format(job_id))
            return False

    def _update_archive_data(self) -> bool:
        """
        Update our Dput configuration and other data, after learning about the master
        server's archive configuration.
        """
        import configparser

        reply_data = None
        try:
            reply_data = self._conn.request_archive_info()
        except ServerErrorException as e:
            log.warning(str(e))
            return False
        except Exception as e:
            log.error('Error when requesting job: {}'.format(str(e)))
            return False

        dput_fname = self._conf.dput_cf_fname

        dputcf = configparser.ConfigParser()
        if os.path.isfile(dput_fname):
            dputcf.read(dput_fname)

        repos = reply_data.get('archive_repos')
        if not repos:
            log.warning('Received no repository data from server!')

        have_data = False
        for repo_name, data in repos.items():
            method = data['upload_method']
            fqdn = data['upload_fqdn']
            if not method or not fqdn:
                log.warning('Unable to upload to %s: No upload destination known.', repo_name)
                continue

            d = dict(
                login='anonymous',
                allow_unsigned_uploads='0',
                fqdn=fqdn,
                method=method,
                incoming=repo_name,
            )
            dputcf[repo_name] = d
            have_data = True

        if have_data:
            with open(dput_fname, 'w', encoding='utf-8') as f:
                dputcf.write(f)

            return True
        else:
            return False

    def run(self):
        """Worker main loop"""

        # the primary worker is responsible for updating the dput.cf
        # file and store knowledge about the archive
        if self._is_primary:
            while not self._update_archive_data():
                time.sleep(30)

        # process jobs
        while True:
            if not self._request_job():
                time.sleep(30)  # wait 30s before trying again
