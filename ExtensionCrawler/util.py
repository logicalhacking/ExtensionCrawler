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
#

""" Various utility methods."""

from time import sleep
from random import random

def google_dos_protection(maxrange=0.3):
    """Wait a random number of seconds (between 0.5 to 0.5+maxrange)
       to avoid Google's bot detection"""
    sleep(0.5+(random()*maxrange))

def value_of(value, default):
    """Get value or default value if None."""
    if value is not None and value is not "":
        return value
    else:
        return default
