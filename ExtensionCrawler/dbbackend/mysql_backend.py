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

from ExtensionCrawler.config import *
import MySQLdb
import _mysql_exceptions
import atexit
import time
from ExtensionCrawler.util import log_info, log_error, log_exception

db = None


def close_db():
    if db is not None:
        db.close()


atexit.register(close_db)


class MysqlBackend:
    def retry(self, f):
        for t in range(const_mysql_maxtries()):
            try:
                return f()
            except _mysql_exceptions.OperationalError as e:
                last_exception = e
                if t + 1 == const_mysql_maxtries():
                    log_exception("MySQL connection eventually failed!", 3,
                                  self.ext_id)
                    raise last_exception
                else:
                    log_exception(
                        """Exception on mysql connection attempt {} of {}, """
                        """wating {}s before retrying...""".format(
                            t + 1,
                            const_mysql_maxtries(),
                            const_mysql_try_wait()), 3, self.ext_id)
                    time.sleep(const_mysql_try_wait())

    def __init__(self, ext_id, **kwargs):
        self.ext_id = ext_id
        self.dbargs = kwargs

    def __enter__(self):
        global db
        if db is None:
            db = self.retry(lambda: MySQLdb.connect(**self.dbargs))
        self.cursor = self.retry(lambda: db.cursor())

        return self

    def __exit__(self, *args):
        self.retry(lambda: db.commit())
        self.retry(lambda: self.cursor.close())

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
        self.retry(lambda: self.cursor.executemany(query, args))

    def insert(self, table, **kwargs):
        self.insertmany(table, [kwargs])

    def get_etag(self, extid, date):
        return self.get_single_value(
            """SELECT crx_etag from extension where extid=%s and date=%s""",
            (extid, date))

    def convert_date(self, date):
        return date[:-6]
