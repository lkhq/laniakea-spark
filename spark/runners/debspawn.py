# -*- coding: utf-8 -*-
#
# Copyright (c) 2012-2013 Paul Tagliamonte <paultag@debian.org>
# Copyright (c) 2016-2018 Matthias Klumpp <mak@debian.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

from firehose.model import Stats
import firehose.parsers.gcc as fgcc

from datetime import timedelta
from io import StringIO
import glob
import re
import os

from spark.utils.firehose import create_firehose
from spark.utils.command import run_logged, run_command, safe_run


STATS = re.compile("Build needed (?P<time>.*), (?P<space>.*) dis(c|k) space")


def parse_debspawn_log(log, sut):
    gccversion = None
    stats = None

    for line in log.splitlines():
        flag = "Toolchain package versions: "
        stat = STATS.match(line)
        if stat:
            info = stat.groupdict()
            hours, minutes, seconds = [int(x) for x in info['time'].split(":")]
            timed = timedelta(hours=hours, minutes=minutes, seconds=seconds)
            stats = Stats(timed.total_seconds())
        if line.startswith(flag):
            line = line[len(flag):].strip()
            packages = line.split(" ")
            versions = {}
            for package in packages:
                if "_" not in package:
                    continue
                b, bv = package.split("_", 1)
                versions[b] = bv
            vs = list(filter(lambda x: x.startswith("gcc"), versions))
            if vs == []:
                continue
            vs = vs[0]
            gccversion = versions[vs]

    obj = fgcc.parse_file(
        StringIO(log),
        sut=sut,
        gccversion=gccversion,
        stats=stats
    )

    return obj


def debspawn_build(jlog, dsc, maintainer, suite, affinity, build_arch, build_indep, analysis):
    if not dsc.endswith('.dsc'):
        raise ValueError("WTF")

    ds_cmd = ['debspawn',
              'build',
              '--no-buildlog',
              '--arch={affinity}'.format(affinity=affinity),
              '--results-dir={cwd}'.format(cwd=os.getcwd())]

    if build_arch and not build_indep:
        ds_cmd.append('--only=arch')
    elif not build_arch and build_indep:
        ds_cmd.append('--only=indep')
    else:
        ds_cmd.append('--only=binary')
    if maintainer:
        ds_cmd.append('--maintainer={maintainer}'.format(maintainer=maintainer))
    ds_cmd.append(suite)
    ds_cmd.append(dsc)

    ret, out = run_logged(jlog, ds_cmd, True)
    for line in out.splitlines():
        if line.startswith('ERROR'):
            if line.startswith('ERROR: The container image for') or \
               line.startswith('ERROR: Build environment setup failed.'):
                # FIXME: This error is not the build's fault!
                # we should reflect that somehow.
                return (analysis, out, True, None)

    ftbfs = ret != 0
    base, _ = os.path.basename(dsc).rsplit(".", 1)
    changes = glob.glob("{base}_*.changes".format(base=base))

    return (analysis, out, ftbfs, changes)


def checkout(dsc_url):
    safe_run(["dget", "-u", "-d", dsc_url])
    return os.path.basename(dsc_url)


def get_version():
    out, err, ret = run_command([
        "debspawn", '--version'
    ])
    if ret != 0:
        raise Exception("debspawn is not installed")
    return ('debspawn', out.strip())


def run(jlog, job, jdata):
    arch_name = job['architecture']
    build_arch = arch_name != "all"
    build_indep = arch_name == "all" or jdata['do_indep']
    maintainer = jdata.get('maintainer')

    firehose = create_firehose('source',
                               jdata['package_name'],
                               jdata['package_version'],
                               build_arch,
                               get_version)

    dsc = checkout(jdata['dsc_url'])
    firehose, out, ftbfs, changes, = \
        debspawn_build(jlog, dsc, maintainer, jdata['suite'], arch_name, build_arch, build_indep, firehose)

    if not changes and not ftbfs:
        print(out)
        print(changes)
        print(list(glob.glob("*")))
        raise Exception("Um. No changes but no FTBFS.")

    if not ftbfs:
        changes = os.path.join(os.getcwd(), changes[0])
    else:
        changes = None

    _, _, v = jdata['package_version'].rpartition(":")
    prefix = "%s_%s_%s.%s" % (jdata['package_name'], v, arch_name, job['uuid'])
    firehose_fname = '{prefix}.firehose.xml'.format(prefix=prefix)

    files = list()
    with open(firehose_fname, 'wb') as fd:
        fd.write(firehose.to_xml_bytes())
    files.append(os.path.abspath(firehose_fname))

    return not ftbfs, files, changes
