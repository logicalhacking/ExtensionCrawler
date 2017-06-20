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
from ExtensionCrawler.util import *
from ExtensionCrawler.crx import *
from ExtensionCrawler.archive import *

import sqlite3
import re
from bs4 import BeautifulSoup
from zipfile import ZipFile
import json
import os
import glob


def setup_tables(con):
    con.execute("""CREATE TABLE review ("""
                """id INTEGER PRIMARY KEY,"""
                """extid TEXT,"""
                """date TEXT,"""
                """author TEXT,"""
                """displayname TEXT,"""
                """reviewdate INTEGER,"""
                """rating INTEGER,"""
                """language TEXT,"""
                """shortauthor TEXT,"""
                """comment TEXT"""
                """)""")
    con.execute("""CREATE TABLE category ("""
                """extid TEXT,"""
                """date TEXT,"""
                """category TEXT,"""
                """PRIMARY KEY (extid, date, category)"""
                """)""")
    con.execute("""CREATE TABLE permission ("""
                """crx_etag TEXT,"""
                """permission TEXT,"""
                """PRIMARY KEY (crx_etag, permission)"""
                """)""")
    con.execute("""CREATE TABLE crx ("""
                """etag TEXT PRIMARY KEY,"""
                """filename TEXT,"""
                """publickey BLOB"""
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
                """fulldescription TEXT,"""
                """developer TEXT,"""
                """crx_etag TEXT,"""
                """lastupdated TEXT,"""
                """PRIMARY KEY (extid, date),"""
                """FOREIGN KEY (crx_etag) REFERENCES crx(etag)"""
                """)""")


def get_etag(ext_id, datepath, con):
    #Trying to parse header file for etag
    headerpath = next(
        iter(glob.glob(os.path.join(datepath, "*.crx.headers"))), None)
    if headerpath:
        with open(headerpath) as f:
            headers = eval(f.read())
            if "ETag" in headers:
                return headers["ETag"]

    #Trying to look up previous etag in database
    linkpath = next(
        iter(glob.glob(os.path.join(datepath, "*.crx.link"))), None)
    if linkpath:
        with open(linkpath) as f:
            link = f.read()
            linked_date = link[3:].split("/")[0]

            row = next(
                con.execute(
                    "SELECT crx_etag FROM extension WHERE extid=? AND date=?",
                    (ext_id, linked_date)), None)
            if row:
                return row[0]


def get_overview_status(datepath):
    overviewstatuspath = os.path.join(datepath, "overview.html.status")
    if os.path.exists(overviewstatuspath):
        with open(overviewstatuspath) as f:
            return int(f.read())


def get_crx_status(datepath):
    statuspath = next(
        iter(glob.glob(os.path.join(datepath, "*.crx.status"))), None)
    if statuspath:
        with open(statuspath) as f:
            return int(f.read())

    # If the extension is paid, we will find a main.headers file...
    statuspath = os.path.join(datepath, "main.status")
    if os.path.exists(statuspath):
        with open(statuspath) as f:
            return int(f.read())

    # ... or an default.crx.headers file
    statuspath = os.path.join(datepath, "default.crx.status")
    if os.path.exists(statuspath):
        with open(statuspath) as f:
            return int(f.read())


def parse_and_insert_overview(ext_id, date, datepath, con):
    overview_path = os.path.join(datepath, "overview.html")
    if os.path.exists(overview_path):
        with open(overview_path) as overview_file:
            contents = overview_file.read()

            # Extract extension name
            match = re.search("""<meta itemprop="name" content="(.*?)"\s*/>""",
                              contents)
            name = match.group(1) if match else None

            # Extract extension version
            match = re.search(
                """<meta itemprop="version" content="(.*?)"\s*/>""", contents)
            version = match.group(1) if match else None

            # Extracts extension categories
            match = re.search(
                """Attribute name="category">(.+?)</Attribute>""", contents)
            categories = match.group(1).split(",") if match else None

            # Extracts the number of downloads
            match = re.search("""user_count.*?(\d+)""", contents)
            downloads = int(match.group(1)) if match else None

            # Extracts the full extension description as it appears on the overview page
            doc = BeautifulSoup(contents, 'html.parser')

            description_parent = doc.find('div', itemprop="description")
            description = str(
                description_parent.contents[0]
            ) if description_parent and description_parent.contents else None
            full_description = str(
                description_parent.parent) if description_parent else None

            developer_parent = doc.find(
                class_=lambda cls: cls and "e-f-Me" in cls)
            developer = str(
                developer_parent.contents[0]) if developer_parent else None

            last_updated_parent = doc.find(
                class_=lambda cls: cls and "h-C-b-p-D-xh-hh" in cls)
            last_updated = str(last_updated_parent.contents[
                0]) if last_updated_parent else None

            etag = get_etag(ext_id, datepath, con)

            con.execute("INSERT INTO extension VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (ext_id, date, name, version, description, downloads,
                         full_description, developer, etag, last_updated))

            if categories:
                for category in categories:
                    con.execute("INSERT INTO category VALUES (?,?,?)",
                                (ext_id, date, category))


def parse_and_insert_crx(ext_id, date, datepath, con):
    crx_path = next(iter(glob.glob(os.path.join(datepath, "*.crx"))), None)
    if crx_path:
        filename = os.path.basename(crx_path)

        with ZipFile(crx_path) as f:
            etag = get_etag(ext_id, datepath, con)
            with f.open("manifest.json") as m:
                try:
                    # There are some manifests that seem to have weird encodings...
                    manifest = json.loads(m.read().decode("utf-8-sig"))
                    if "permissions" in manifest:
                        for permission in manifest["permissions"]:
                            con.execute(
                                "INSERT OR REPLACE INTO permission VALUES (?,?)",
                                (etag, str(permission)))
                except json.decoder.JSONDecodeError:
                    pass

            public_key = read_crx(crx_path).pk

            con.execute("INSERT INTO crx VALUES (?,?,?)", (etag, filename,
                                                           public_key))


def get(d, k):
    if d and k in d:
        return d[k]


def parse_and_insert_review(ext_id, date, reviewpath, con):
    with open(reviewpath) as f:
        content = f.read()
        stripped = content[content.find('{"'):]
        d = json.JSONDecoder().raw_decode(stripped)
        annotations = get(next(iter(d), None), "annotations")
        if annotations:
            for review in d[0]["annotations"]:
                timestamp = get(review, "timestamp")
                starRating = get(review, "starRating")
                comment = get(review, "comment")
                displayname = get(get(review, "entity"), "displayName")
                author = get(get(review, "entity"), "author")
                language = get(get(review, "entity"), "language")
                shortauthor = get(get(review, "entity"), "shortAuthor")

                con.execute("INSERT INTO review VALUES(?,?,?,?,?,?,?,?,?,?)",
                            (None, ext_id, date, author, displayname,
                             timestamp, starRating, language, shortauthor,
                             comment))


def parse_and_insert_status(ext_id, date, datepath, con):
    overview_status = get_overview_status(datepath)
    crx_status = get_crx_status(datepath)

    overviewexceptionpath = os.path.join(datepath, "overview.html.exception")
    overview_exception = None
    if os.path.exists(overviewexceptionpath):
        with open(overviewexceptionpath) as f:
            overview_exception = f.read()

    con.execute("INSERT INTO status VALUES (?,?,?,?,?)",
                (ext_id, date, crx_status, overview_status,
                 overview_exception))


def update_sqlite_incremental(archivedir, tmptardir, ext_id, date, verbose,
                              indent):
    txt = ""
    indent2 = indent + 4 * " "

    db_path = db_file(archivedir, ext_id)
    datepath = os.path.join(tmptardir, date)

    txt = logmsg(verbose, txt,
                 indent + "- updating with data from {}\n".format(date))

    if not os.path.exists(db_path):
        txt = logmsg(verbose, txt,
                     indent2 + "* db file does not exist, creating...\n")
        with sqlite3.connect(db_path) as con:
            setup_tables(con)

    with sqlite3.connect(db_path) as con:
        parse_and_insert_status(ext_id, date, datepath, con)

        parse_and_insert_overview(ext_id, date, datepath, con)

        crx_path = next(iter(glob.glob(os.path.join(datepath, "*.crx"))), None)

        etag = get_etag(ext_id, datepath, con)
        etag_already_in_db = next(
            con.execute("SELECT COUNT(etag) FROM crx WHERE etag=?", (etag, )))[
                0]

        if etag:
            if not etag_already_in_db:
                try:
                    parse_and_insert_crx(ext_id, date, datepath, con)
                except zipfile.BadZipfile as e:
                    txt = logmsg(
                        verbose, txt, indent2 +
                        "* WARNING: the found crx file is not a zip file, exception: "
                    )
                    txt = logmsg(verbose, txt, str(e))
                    txt = logmsg(verbose, txt, "\n")
        else:
            crx_status = get_crx_status(datepath)
            if crx_status != 401 and crx_status != 204:
                txt = logmsg(verbose, txt,
                             indent2 + "* WARNING: could not find etag\n")

        reviewpaths = glob.glob(os.path.join(datepath, "reviews*.text"))
        for reviewpath in reviewpaths:
            try:
                parse_and_insert_review(ext_id, date, reviewpath, con)
            except json.decoder.JSONDecodeError as e:
                txt = logmsg(
                    verbose, txt,
                    indent2 + "* Could not parse review file, exception: ")
                txt = logmsg(verbose, txt, str(e))
                txt = logmsg(verbose, txt, "\n")
    return txt
