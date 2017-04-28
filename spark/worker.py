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
import sys
import asyncio
import logging as log
import threading

import zmq


class Worker:

    def __init__(self):
        self._running = False


    def _run(self):
        print ("HELLO!")

        backendsock = self._zctx.socket(zmq.DEALER)
        backendsock.connect('inproc://backend')
        backendsock.send_string("BLAH")

        loop = asyncio.get_event_loop()
        loop.run_forever()
        self._running = False


    @property
    def is_running(self):
        return self._running


    def start(self, job_name):
        assert(not self.running)

        t = threading.Thread(target=self._run)
        t.daemon = True  # thread dies when main thread (only non-daemon thread) exits.
        t.name = job_name
        t.start()
