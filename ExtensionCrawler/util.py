#!/usr/bin/env python3.6
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

import traceback
import logging
import sys

from ExtensionCrawler.config import const_log_format


def value_of(value, default):
    """Get value or default value if None."""
    if value is not None and value is not "":
        return value
    else:
        return default


def log_debug(msg, indent_level=0, extid="-" * 32):
    logging.debug(str(extid) + " " + 4 * indent_level * " " + str(msg))


def log_info(msg, indent_level=0, extid="-" * 32):
    logging.info(str(extid) + " " + 4 * indent_level * " " + str(msg))


def log_warning(msg, indent_level=0, extid="-" * 32):
    logging.warning(str(extid) + " " + 4 * indent_level * " " + str(msg))


def log_error(msg, indent_level=0, extid="-" * 32):
    logging.error(str(extid) + " " + 4 * indent_level * " " + str(msg))


def log_exception(msg, indent_level=0, extid="-" * 32):
    logging.error(str(extid) + " " + 4 * indent_level * " " + str(msg))
    for line in traceback.format_exc().splitlines():
        logging.error(str(extid) + " " + 4 * indent_level * " " + line)


def setup_logger(verbose):
    if verbose:
        loglevel = logging.INFO
    else:
        loglevel = logging.WARNING

    logger = logging.getLogger()
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(logging.Formatter(const_log_format()))
    logger.addHandler(ch)
    logger.setLevel(loglevel)
