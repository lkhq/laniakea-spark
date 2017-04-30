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
import subprocess
import select
import time
from contextlib import contextmanager


def run_logged(jlog, cmd, **kwargs):
    p = subprocess.Popen(cmd, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)

    sel = select.poll()
    sel.register(p.stdout, select.POLLIN)
    while True:
        if sel.poll(1):
            jlog.write(p.stdout.read())
        else:
            time.sleep(1) # wait a little for the process to write more output
        if p.poll() is not None:
            if sel.poll(1):
                jlog.write(p.stdout.read())
            break
    ret = p.poll()
    if ret:
        jlog.write('Command {0} failed with error code {1}'.format(cmd, ret))
    return ret


def sign(jlog, changes, gpg):
    if changes.endswith(".dud"):
        r = run_logged(jlog, ['gpg', '-u', gpg, '--clearsign', changes])
        if r:
            raise Exception('Unable to run GPG.')
        os.rename("%s.asc" % (changes), changes)
    else:
        r = run_logged(jlog, ['debsign', '-k', gpg, changes])
        if r:
            raise Exception('Unable to run debsign.')


def upload(jlog, changes, gpg, host):
    sign(jlog, changes, gpg)
    return run_logged(jlog, ['dput', host, changes])


@contextmanager
def cd(where):
    ncwd = os.getcwd()
    try:
        yield os.chdir(where)
    finally:
        os.chdir(ncwd)
