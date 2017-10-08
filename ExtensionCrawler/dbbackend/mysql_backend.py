#
# Copyright (C) 2017 The University of Sheffield, UK
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

import time
import datetime
from random import uniform
from itertools import starmap

import MySQLdb
import _mysql_exceptions

import ExtensionCrawler.config as config
from ExtensionCrawler.util import log_info, log_error, log_exception


class MysqlBackend:
    def __init__(self, ext_id, try_wait=config.const_mysql_try_wait(), maxtries=config.const_mysql_maxtries(), **kwargs):
        self.ext_id = ext_id
        self.dbargs = kwargs
        self.try_wait = try_wait
        self.maxtries = maxtries
        self.cache = {}
        self.db = None
        self.cursor = None

    def __enter__(self):
        self._create_conn()
        return self

    def __exit__(self, *args):
        start = time.time()
        self.retry(self._commit_cache)
        self.db.commit()
        log_info(
            "* Database batch insert finished after {}".format(
                datetime.timedelta(seconds=int(time.time() - start))),
            3,
            self.ext_id)
        self._close_conn()

    def _commit_cache(self):
        for query, args in self.cache.items():
            self.cursor.executemany(query, args)

    def _create_conn(self):
        if self.db is None:
            self.db = MySQLdb.connect(**self.dbargs)
        if self.cursor is None:
            self.cursor = self.db.cursor()

    def _close_conn(self):
        if self.cursor is not None:
            self.cursor.close()
            self.cursor = None
        if self.db is not None:
            self.db.close()
            self.db = None

    def retry(self, f):
        for t in range(self.maxtries):
            try:
                self._create_conn()
                return f()
            except _mysql_exceptions.OperationalError as e:
                last_exception = e

                try:
                    self._close_conn()
                except Exception as e2:
                    log_error("Surpressed exception: {}".format(str(e2)), 3,
                              self.ext_id)

                if t + 1 == self.maxtries:
                    log_error(
                        "MySQL connection eventually failed, closing connection!",
                        3, self.ext_id)
                    raise last_exception
                else:
                    factor = 0.2
                    logmsg = ("Exception on mysql connection attempt "
                              "{} of {}, wating {}s +/- {}% before retrying..."
                              ).format(t + 1,
                                       self.maxtries,
                                       self.try_wait, factor * 100)
                    log_warning(logmsg, 3, self.ext_id)
                    time.sleep(self.try_wait * uniform(
                        1 - factor, 1 + factor))

    def get_single_value(self, query, args):
        self.retry(lambda: self.cursor.execute(query, args))

        result = self.retry(lambda: self.cursor.fetchone())
        if result is not None:
            return result[0]
        else:
            return None

    def insertmany(self, table, arglist):
        args = [tuple(arg.values()) for arg in arglist]

        # Looks like this, for example:
        # INSERT INTO category VALUES(extid,date,category) (%s,%s,%s)
        #   ON DUPLICATE KEY UPDATE extid=VALUES(extid),date=VALUES(date)
        #   ,category=VALUES(category)
        query = "INSERT INTO {}({}) VALUES ({}) ON DUPLICATE KEY UPDATE {}".format(
            table,
            ",".join(arglist[0].keys()),
            ",".join(len(args[0]) * ["%s"]),
            ",".join(
                ["{c}=VALUES({c})".format(c=c) for c in arglist[0].keys()]))
        if query not in self.cache:
            self.cache[query] = []
        self.cache[query] += args

    def insert(self, table, **kwargs):
        self.insertmany(table, [kwargs])

    def get_etag(self, extid, date):
        return self.get_single_value(
            """SELECT crx_etag from extension where extid=%s and date=%s""",
            (extid, date))

    def convert_date(self, date):
        return date[:-6]
