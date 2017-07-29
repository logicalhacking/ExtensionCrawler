#!/usr/bin/env python3
#
# Copyright (C) 2016,2017 The University of Sheffield, UK
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

""" Various utility methods."""

import sys
from time import sleep
from random import random

def google_dos_protection(maxrange=2.2):
    """Wait a random number of seconds (between 0.5 to maxrange*0.5)
       to avoid Google's bot detection"""
    sleep((1+random())*(maxrange/2.0)*.5)

def log(verbose, msg):
    """Print log message."""
    if verbose:
        sys.stdout.write(msg)
        sys.stdout.flush()

def logmsg(verbose, msg1, msg2):
    """Append msg2 to log stream msg1."""
    if verbose:
        return msg1 + msg2
    else:
        return msg1

def value_of(value, default):
    """Get value or default value if None."""
    if value is not None and value is not "":
        return value
    else:
        return default
