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
import subprocess
import select
import time
from contextlib import contextmanager
from schroot.chroot import SchrootChroot


@contextmanager
def spark_schroot(name, job_id):
    ncwd = os.getcwd()
    ch = SchrootChroot()

    # the workspace dir name inside the chroot
    wsdir = '/workspaces/{}'.format(job_id)
    results_dir = '/workspaces/{}/result'.format(job_id)

    try:
        # change to neutral directory
        os.chdir('/tmp')
        ch.start(name)
        yield (ch, wsdir, results_dir)
    finally:
        try:
            # hack to allow the worker to delete the newly created files
            ch.run([
                'chmod', '-R', '777', wsdir
            ], user='root')
        except:
            pass

        ch.end()
        os.chdir(ncwd)


def chroot_run_logged(schroot, jlog, cmd, **kwargs):
    p = schroot.Popen(cmd, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    sel = select.poll()
    sel.register(p.stdout, select.POLLIN)
    while True:
        if sel.poll(2):
            jlog.write(p.stdout.read())
        else:
            time.sleep(4) # wait a little for the process to write more output
        if p.poll() is not None:
            if sel.poll(1):
                jlog.write(p.stdout.read())
            break
    ret = p.returncode
    if ret:
        jlog.write('Command {0} failed with error code {1}'.format(cmd, ret))
    return ret


def chroot_copy(chroot, what, whence, user=None):
    import shutil
    with chroot.create_file(whence, user) as f:
        with open(what, 'rb') as src:
            shutil.copyfileobj(src, f)


def chroot_upgrade(chroot, jlog):
    ret = chroot_run_logged(chroot, jlog, [
        'apt-get', 'update'
    ], user='root')
    if ret:
        return False

    ret = chroot_run_logged(chroot, jlog, [
        'apt-get', 'full-upgrade', '-y'
    ], user='root')
    if ret:
        return False
    return True
