# -*- coding: utf-8 -*-
#
# Copyright (C) 2017-2018 Matthias Klumpp <matthias@tenstral.net>
# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
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

import logging as log

from firehose.model import Analysis, Metadata, Generator, DebianBinary, DebianSource


def generate_sut_from_source(name, version, arch):
    local = None
    if "-" in version:
        version, local = version.rsplit("-", 1)
    return DebianSource(name, version, local)


def generate_sut_from_binary(name, version, arch):
    local = None
    if "-" in version:
        version, local = version.rsplit("-", 1)
    return DebianBinary(name, version, local, arch)


def create_firehose(ptype, package_name, package_version, arch, version_getter):
    log.debug("Initializing empty firehose report")
    sut = {"source": generate_sut_from_source, "binary": generate_sut_from_binary}[ptype](
        package_name, package_version, arch
    )

    gname_, gversion = version_getter()
    gname = "laniakea-spark/%s" % gname_

    return Analysis(
        metadata=Metadata(
            generator=Generator(name=gname, version=gversion), sut=sut, file_=None, stats=None
        ),
        results=[],
    )
