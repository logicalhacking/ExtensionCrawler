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

db = None


def close_db():
    if db is not None:
        db.close()


atexit.register(close_db)

def retry(f):
    for t in range(const_mysql_maxtries()):
        try:
            return f()
        except _mysql_exceptions.OperationalError as e:
            last_exception = e
        if t + 1 == const_mysql_maxtries():
            raise last_exception
        else:
            time.sleep(const_mysql_try_wait())


class MysqlBackend:
    def __init__(self, **kwargs):
        self.dbargs = kwargs

    def __enter__(self):
        global db
        if db is None:
            db = retry(lambda: MySQLdb.connect(**self.dbargs))
        self.cursor = retry(lambda: db.cursor())

        return self

    def __exit__(self, *args):
        retry(lambda: db.commit())
        retry(lambda: self.cursor.close())

    def get_single_value(self, query, args):
        retry(lambda: self.cursor.execute(query, args))

        result = retry(lambda: self.cursor.fetchone())
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
        retry(lambda: self.cursor.executemany(query, args))

    def insert(self, table, **kwargs):
        self.insertmany(table, [kwargs])

    def get_most_recent_etag(self, extid, date):
        return self.get_single_value(
            """SELECT crx_etag from extension e1 where extid=%s and date<%s and not exists """
            """(select 1 from extension e2 where e2.extid=e1.extid and e2.date<e1.date)""",
            (extid, date))

    def etag_already_in_db(self, etag):
        return self.get_single_value(
            "SELECT COUNT(crx_etag) FROM crx WHERE crx_etag=%s", (etag, ))

    def convert_date(self, date):
        return date[:-6]
