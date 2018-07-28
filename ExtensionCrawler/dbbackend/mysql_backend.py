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
from collections import OrderedDict
from random import uniform
import sys

import MySQLdb
import _mysql_exceptions

import ExtensionCrawler.config as config
from ExtensionCrawler.util import log_info, log_error, log_warning


class MysqlBackend:
    def __init__(self, ext_id, delayed=False, cache_etags=False, try_wait=config.const_mysql_try_wait(), maxtries=config.const_mysql_maxtries(),
                 **kwargs):
        self.ext_id = ext_id
        self.delayed = delayed
        self.cache_etags = cache_etags
        self.dbargs = kwargs
        self.try_wait = try_wait
        self.maxtries = maxtries
        self.cache = {}
        self.crx_etag_cache = {}
        self.db = None
        self.cursor = None

    def __enter__(self):
        self._create_conn()
        return self

    def __exit__(self, *args):
        for table, arglist in self.cache.items():
            self._do_insert(table, arglist)
            self.cache[table] = []
        self._close_conn()

    def _get_column_names(self, table):
        self.cursor.execute(f"select column_name from information_schema.columns where table_schema=database() and table_name=%s", (table,))
        return [row[0] for row in self.cursor.fetchall()]


    def _do_insert(self, table, arglist):
        if len(arglist) == 0:
            return
        sorted_arglist = self.sort_by_primary_key(table, arglist)
        args = [tuple(arg.values()) for arg in sorted_arglist]

        if self.delayed:
            query = "INSERT DELAYED INTO {}({}) VALUES ({})".format(
                table,
                ",".join(sorted_arglist[0].keys()),
                ",".join(len(args[0]) * ["%s"]))
        else:
            column_names = self.retry(lambda: self._get_column_names(table))
            if "last_modified" in column_names:
                additional_columns = ["last_modified"]
            else:
                additional_columns = []
            # Looks like this, for example:
            # INSERT INTO category VALUES(extid,date,category) (%s,%s,%s)
            #   ON DUPLICATE KEY UPDATE extid=VALUES(extid),date=VALUES(date)
            #   ,category=VALUES(category)
            query = "INSERT INTO {}({}) VALUES ({}) ON DUPLICATE KEY UPDATE {}".format(
                table,
                ",".join(sorted_arglist[0].keys()),
                ",".join(len(args[0]) * ["%s"]),
                ",".join(
                    ["{c}=VALUES({c})".format(c=c) for c in list(sorted_arglist[0].keys()) + additional_columns]))
        start = time.time()
        self.retry(lambda: self.cursor.executemany(query, args))
        log_info("* Inserted {} bytes into {}, taking {}.".format(sum([sys.getsizeof(arg) for arg in args]),
                                                                       table, datetime.timedelta(seconds=int(time.time() - start))), 3)

    def _create_conn(self):
        if self.db is None:
            log_info("* self.db is None,  open new connection ...", 3)
            self.db = MySQLdb.connect(**self.dbargs)
            self.db.autocommit(True)
            log_info("* success", 4)
        if self.cursor is None:
            log_info("* self.cursor is None,  assigning new cursor ...", 3)
            self.cursor = self.db.cursor()
            log_info("* success", 4)

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
                    log_error("Suppressed exception: {}".format(str(e2)), 3)

                if t + 1 == self.maxtries:
                    log_error("MySQL connection eventually failed, closing connection!", 3)
                    raise last_exception
                else:
                    factor = 0.2
                    logmsg = ("Exception on mysql connection attempt "
                              "{} of {}, wating {}s +/- {}% before retrying..."
                              ).format(t + 1,
                                       self.maxtries,
                                       self.try_wait, factor * 100)
                    log_warning(logmsg, 3)
                    time.sleep(self.try_wait * uniform(
                        1 - factor, 1 + factor))

    def get_single_value(self, query, args):
        self.retry(lambda: self.cursor.execute(query, args))

        result = self.retry(lambda: self.cursor.fetchone())
        if result is not None:
            return result[0]
        else:
            return None

    def sort_by_primary_key(self, table, arglist):
        self.retry(lambda: self.cursor.execute(f"SHOW KEYS FROM {table} WHERE Key_name = 'PRIMARY'"))
        primary_keys = [row[4] for row in self.cursor.fetchall()]

        sorted_arglist = sorted(arglist, key=lambda x: [x[pk] for pk in primary_keys])

        def arglist_shuffler(x):
            try:
                return primary_keys.index(x)
            except ValueError:
                return len(primary_keys)
        shuffled_arglist = [OrderedDict(sorted(arg.items(), key=lambda x: arglist_shuffler(x[0]))) for arg in sorted_arglist]
        return shuffled_arglist


    def insertmany(self, table, arglist):
        if table not in self.cache:
            self.cache[table] = []
        self.cache[table] += arglist
        if len(self.cache[table]) >= 128:
            self._do_insert(table, self.cache[table])
            self.cache[table] = []
        if self.cache_etags and table == "extension":
            for arg in arglist:
                self.crx_etag_cache[(arg["extid"], arg["date"])] = arg["crx_etag"]

    def insert(self, table, **kwargs):
        self.insertmany(table, [kwargs])

    def get_etag(self, extid, date):
        if (extid, date) in self.crx_etag_cache:
            return self.crx_etag_cache[(extid, date)]
        else:
            return None

    def get_cdnjs_info(self, md5):
        query = """SELECT library, version, filename, add_date, typ from cdnjs where md5=%s"""
        args = [md5]
        self.retry(lambda: self.cursor.execute(query, args))
        result = self.retry(lambda: self.cursor.fetchone())
        return result


def convert_date(date):
    return date[:-6]
