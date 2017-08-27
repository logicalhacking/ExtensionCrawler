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

import MySQLdb
import atexit

db = None


def close_db():
    if db is not None:
        db.close()


atexit.register(close_db)


class MysqlBackend:
    def __init__(self, **kwargs):
        self.dbargs = kwargs

    def __enter__(self):
        global db
        if db is None:
            db = MySQLdb.connect(**self.dbargs)
        self.cursor = db.cursor()

        self.columns = {}
        self.cursor.execute(
            "select table_name,column_name from information_schema.columns where table_schema=%s",
            (self.dbargs["db"], ))
        for table, column in self.cursor.fetchall():
            if table not in self.columns:
                self.columns[table] = []
            self.columns[table] += [column]

        return self

    def __exit__(self, *args):
        db.commit()
        self.cursor.close()

    def get_single_value(self, query, args):
        self.cursor.execute(query, args)

        result = self.cursor.fetchone()
        if result is not None:
            return result[0]
        else:
            return None

    def insertmany(self, table, arglist):
        args = [
            tuple([arg[k] for k in self.columns[table]]) for arg in arglist
        ]
        # Looks like this, for example:
        # INSERT INTO category VALUES (%s,%s,%s) ON DUPLICATE KEY UPDATE extid=VALUES(extid),date=VALUES(date),category=VALUES(category)
        query = "INSERT INTO {} VALUES ({}) ON DUPLICATE KEY UPDATE {}".format(
            table,
            ",".join(len(args[0]) * ["%s"]),
            ",".join(
                ["{c}=VALUES({c})".format(c=c) for c in self.columns[table]]))
        self.cursor.executemany(query, args)

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
