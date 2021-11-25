# -*- coding: utf-8 -*-
#
# Copyright (C) 2016-2018 Matthias Klumpp <matthias@tenstral.net>
# Copyright (C) 2012-2013 Paul Tagliamonte <paultag@debian.org>
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

import shlex
import subprocess
from io import StringIO


class SubprocessError(Exception):
    def __init__(self, out, err, ret, cmd):
        self.out = out
        self.err = err
        self.ret = ret
        self.cmd = cmd
        super(SubprocessError, self).__init__(
            "%s: %d\n%s" % (str(self.cmd), self.ret, str(self.err))
        )

    def __str__(self):
        return "%s: %d\n%s" % (str(self.cmd), self.ret, str(self.err))


# Input may be a byte string, a unicode string, or a file-like object
def run_command(command, input=None):
    if not isinstance(command, list):
        command = shlex.split(command)

    if not input:
        input = None
    elif isinstance(input, str):
        input = input.encode('utf-8')
    elif not isinstance(input, bytes):
        input = input.read()

    try:
        pipe = subprocess.Popen(
            command,
            shell=False,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        return (None, None, -1)

    (output, stderr) = pipe.communicate(input=input)
    (output, stderr) = (c.decode('utf-8', errors='ignore') for c in (output, stderr))
    return (output, stderr, pipe.returncode)


def safe_run(cmd, input=None, expected=0):
    if not isinstance(expected, tuple):
        expected = (expected,)

    out, err, ret = run_command(cmd, input=input)

    if ret not in expected:
        raise SubprocessError(out, err, ret, cmd)

    return out, err, ret


def run_logged(jlog, cmd: list[str], return_output=False, **kwargs):
    '''Run a command and log output to the job logfile.

    Parameters
    ----------
    jlog JobLog
        The job log to use
    cmd
        Command to execute
    return_output
        Whether to save the output to return as string when the function completes.

    Returns
    -------
    ret : int
        Return code of the process
    outbuf : str or None
        Process output as string if `return_output` was True
    '''
    p = subprocess.Popen(
        cmd, **kwargs, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False
    )

    # capture live output and send it to all places that are interested in
    # logging it (except for our stdout).
    outbuf = StringIO()
    while True:
        line_b = p.stdout.readline()
        if p.poll() is not None:
            break
        line_s = str(line_b, 'utf-8', 'replace')
        jlog.write(line_s)
        if return_output:
            outbuf.write(line_s)

    ret = p.returncode
    if ret:
        jlog.write('Command {0} failed with error code {1}'.format(' '.join(cmd), ret))

    return ret, outbuf.getvalue()
