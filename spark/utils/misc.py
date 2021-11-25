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
import json
import shutil
import tempfile
from contextlib import contextmanager

from spark.utils.command import safe_run


def sign(changes, gpg):
    if changes.endswith(".dud"):
        safe_run(['gpg', '-u', gpg, '--clearsign', changes])
        os.rename("%s.asc" % (changes), changes)
    else:
        safe_run(['debsign', '-k', gpg, changes])


def upload(changes, gpg, host):
    sign(changes, gpg)
    return safe_run(['dput', host, changes])


@contextmanager
def cd(where):
    ncwd = os.getcwd()
    try:
        yield os.chdir(where)
    finally:
        os.chdir(ncwd)


@contextmanager
def tdir():
    fp = tempfile.mkdtemp()
    try:
        yield fp
    finally:
        shutil.rmtree(fp)


def to_compact_json(json_object, sort_keys=False):
    '''
    Create JSON representation of :json_object in the most
    compact way possible.
    '''
    data = json.dumps(json_object, ensure_ascii=False, separators=(',', ':'), sort_keys=sort_keys)
    return str(data)
