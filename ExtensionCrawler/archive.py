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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import sys
import glob
import re
import requests
from time import sleep
from random import randint
from datetime import datetime, timezone
from ExtensionCrawler.util import *
import dateutil
import dateutil.parser


class Error(Exception):
    pass


class CrawlError(Error):
    def __init__(self, extid, message, pagecontent=""):
        self.extid = extid
        self.message = message
        self.pagecontent = pagecontent


class RequestResult:
    def __init__(self, response=None, exception=None):
        if response is not None:
            self.http_status = response.status_code
        self.exception = exception

    def is_ok(self):
        return (self.exception is None) and (self.http_status==200)

    def not_authorized(self):
        return (self.exception is None) and (self.http_status==401)

    def not_found(self):
        return (self.exception is None) and (self.http_status==404)

    def has_exception(self):
        return self.exception is not None

    def not_available(self):
        return (self.exception is None) and (self.http_status==503)

    def not_modified(self):
        return ((self.exception is None) and (self.http_status==304))


class UpdateResult:
    def __init__(self, id, res_overview, res_crx, res_reviews, res_support):
        self.id = id
        self.res_overview = res_overview
        self.res_crx = res_crx
        self.res_reviews = res_reviews
        self.res_support = res_support

    def is_ok(self):
        return (self.res_overview.is_ok() and (self.res_crx.is_ok() or self.res_crx.not_modified()) and (
            (self.res_reviews is None) or self.res_reviews.is_ok()) and (
                (self.res_support is None) or self.res_support.is_ok()))

    def not_authorized(self):
        return (self.res_overview.not_authorized() or
                self.res_crx.not_authorized() or
                (self.res_reviews is not None and
                 self.res_reviews.not_authorized()) or (
                     self.res_support is not None and
                     self.res_support.not_authorized()))

    def not_in_store(self):
        return (
            self.res_overview.not_found() or self.res_crx.not_found() or
            (self.res_reviews is not None and self.res_reviews.not_found()) or
            (self.res_support is not None and self.res_support.not_found()))

    def has_exception(self):
        return (
            self.res_overview.has_exception() or
            self.res_crx.has_exception() or
            (self.res_reviews is not None and self.res_reviews.has_exception())
            or (self.res_support is not None and
                self.res_support.has_exception()))

    def raised_google_ddos(self):
        return (
            (self.res_reviews is not None and self.res_reviews.not_available())
            or (self.res_support is not None and
                self.res_support.not_available()))

    def not_modified(self):
        return self.res_crx.not_modified()



def get_local_archive_dir(id):
    return "{}/{}".format(id[:3],id)

def get_local_archive_dirs(id):
    return [get_local_archive_dir(id)]

def write_text(dir, fname, text):
    with open(os.path.join(dir, fname), 'w') as f:
        f.write(text)


def store_request_metadata(dir, fname, request):
    write_text(dir, fname + ".headers", str(request.headers))
    write_text(dir, fname + ".status", str(request.status_code))
    write_text(dir, fname + ".url", str(request.url))


def store_request_text(dir, fname, request):
    write_text(dir, fname, request.text)
    store_request_metadata(dir, fname, request)

def httpdate(dt):
    weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
    month = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
        "Nov", "Dec"
    ][dt.month - 1]
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
        weekday, dt.day, month, dt.year, dt.hour, dt.minute, dt.second)


def last_modified_utc_date(path):
    if path is "":
        return ""
    return os.path.split(os.path.dirname(path))[1]


def last_modified_http_date(path):
    if path is "":
        return ""
    return httpdate(dateutil.parser.parse(last_modified_utc_date(path)))
def last_crx(dir, extid):
    old_archives = sorted(
        glob.glob(os.path.join(os.path.dirname(dir), "*/*.crx")))
    last_archive = ""
    if old_archives != []:
        last_archive = old_archives[-1]
    return last_archive


