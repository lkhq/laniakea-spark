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

import importlib


'''
Determine which runner is responsible for which job type.
'''
PLUGINS = {
    "iso-image-build": "spark.runners.iso_build",
    "package-build": "spark.runners.sbuild",
}


def load_module(what):
    path = PLUGINS[what]
    mod = importlib.import_module(path)
    return (mod.run, mod.get_version)
