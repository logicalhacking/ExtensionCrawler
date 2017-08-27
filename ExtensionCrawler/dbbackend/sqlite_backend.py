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

import os
import sqlite3


def setup_fts_tables(con, name, columns, primary_columns):
    sqls = [
        s.format(
            name=name,
            columns=", ".join(columns),
            new_columns=", ".join(["new." + x for x in columns]),
            primary_columns=", ".join(primary_columns))
        for s in [
            """CREATE TABLE {name}({columns}, PRIMARY KEY ({primary_columns}));""",
            """CREATE VIRTUAL TABLE {name}_fts using fts4(content="{name}", {columns});""",
            """CREATE TRIGGER {name}_bu BEFORE UPDATE ON {name} BEGIN """
            """DELETE FROM {name}_fts WHERE docid=old.rowid;"""
            """END;""",
            """CREATE TRIGGER {name}_bd BEFORE DELETE ON {name} BEGIN """
            """DELETE FROM {name}_fts WHERE docid=old.rowid;"""
            """END;""",
            """CREATE TRIGGER {name}_au AFTER UPDATE ON {name} BEGIN """
            """INSERT INTO {name}_fts(docid, {columns}) VALUES(new.rowid, {new_columns});"""
            """END;""",
            """CREATE TRIGGER {name}_ai AFTER INSERT ON {name} BEGIN """
            """INSERT INTO {name}_fts(docid, {columns}) VALUES(new.rowid, {new_columns});"""
            """END;"""
        ]
    ]
    for sql in sqls:
        con.execute(sql)


def setup_tables(con):
    setup_fts_tables(con, "support", [
        "author", "commentdate", "extid", "date", "displayname", "title",
        "language", "shortauthor", "comment"
    ], ["author", "commentdate", "extid", "date"])

    setup_fts_tables(con, "review", [
        "author", "commentdate", "extid", "date", "displayname", "rating",
        "language", "shortauthor", "comment"
    ], ["author", "commentdate", "extid", "date"])

    setup_fts_tables(con, "reply", [
        "author", "commentdate", "extid", "date", "displayname", "replyto",
        "language", "shortauthor", "comment"
    ], ["author", "commentdate", "extid", "date"])

    con.execute("""CREATE TABLE category ("""
                """extid TEXT,"""
                """date TEXT,"""
                """category TEXT,"""
                """PRIMARY KEY (extid, date, category)"""
                """)""")
    con.execute("""CREATE TABLE content_script_url ("""
                """crx_etag TEXT,"""
                """url TEXT,"""
                """PRIMARY KEY (crx_etag, url)"""
                """)""")
    con.execute("""CREATE TABLE permission ("""
                """crx_etag TEXT,"""
                """permission TEXT,"""
                """PRIMARY KEY (crx_etag, permission)"""
                """)""")
    con.execute("""CREATE TABLE crx ("""
                """crx_etag TEXT PRIMARY KEY,"""
                """filename TEXT,"""
                """size INTEGER,"""
                """publickey BLOB"""
                """)""")
    con.execute("""CREATE TABLE jsfile ("""
                """crx_etag TEXT,"""
                """detect_method TEXT,"""
                """filename TEXT,"""
                """type TEXT,"""
                """lib TEXT,"""
                """path TEXT,"""
                """md5 TEXT,"""
                """size INTEGER,"""
                """version TEXT,"""
                """PRIMARY KEY (crx_etag, path)"""
                """)""")
    con.execute("""CREATE TABLE status ("""
                """extid TEXT,"""
                """date TEXT,"""
                """crx_status INTEGER,"""
                """overview_status INTEGER,"""
                """overview_exception TEXT,"""
                """PRIMARY KEY (extid, date)"""
                """)""")
    con.execute("""CREATE TABLE extension ("""
                """extid TEXT,"""
                """date TEXT,"""
                """name TEXT,"""
                """version TEXT,"""
                """description TEXT,"""
                """downloads INTEGER,"""
                """rating REAL,"""
                """ratingcount INTEGER,"""
                """fulldescription TEXT,"""
                """developer TEXT,"""
                """itemcategory TEXT,"""
                """crx_etag TEXT,"""
                """lastupdated TEXT,"""
                """PRIMARY KEY (extid, date),"""
                """FOREIGN KEY (crx_etag) REFERENCES crx(crx_etag)"""
                """)""")


class SqliteBackend:
    def __init__(self, filename):
        self.filename = filename

    def __enter__(self):
        new_db = False
        if not os.path.exists(self.filename):
            new_db = True
        self.con = sqlite3.connect(self.filename)
        if new_db:
            setup_tables(self.con)
        return self

    def __exit__(self, *args):
        self.con.commit()
        self.con.close()

    def get_single_value(self, query, args):
        result = next(self.con.execute(query, args), None)
        if result is not None:
            return result[0]
        else:
            return None

    def etag_already_in_db(self, etag):
        return self.get_single_value(
            "SELECT COUNT(crx_etag) FROM crx WHERE crx_etag=?", (etag, ))

    def insert(self, table, **kwargs):
        args = tuple(kwargs.values())
        self.con.execute("INSERT OR REPLACE INTO {} VALUES ({})".format(
            table, ",".join(len(args) * ["?"])), args)

    def insertmany(self, table, argslist):
        for arg in argslist:
            self.insert(table, **arg)

    def get_most_recent_etag(self, extid, date):
        return self.get_single_value(
            """SELECT crx_etag from extension e1 where extid=? and date<? and not exists """
            """(select 1 from extension e2 where e2.extid=e1.extid and e2.date<e1.date)""",
            (extid, date))
