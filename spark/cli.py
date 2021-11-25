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


def daemon():
    from argparse import ArgumentParser

    parser = ArgumentParser(description="Debile build slave")
    parser.add_argument(
        "--config",
        action="store",
        dest="config",
        default=None,
        help="Path to the slave.yaml config file.",
    )
    parser.add_argument(
        "-s",
        "--syslog",
        action="store_true",
        dest="syslog",
        help="Log to syslog instead of stderr.",
    )
    parser.add_argument(
        "-d", "--debug", action="store_true", dest="debug", help="Enable debug messages to stderr."
    )

    from spark.daemon import Daemon

    d = Daemon()

    d.run()
