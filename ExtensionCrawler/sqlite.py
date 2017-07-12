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
import jsbeautifier
from zipfile import ZipFile
import json
import os
import glob


class SelfclosingSqliteDB:
    def __init__(self, filename):
        self.filename = filename

    def __enter__(self):
        self.con = sqlite3.connect(self.filename)
        return self.con

    def __exit__(self, *args):
        self.con.commit()
        self.con.close()


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
                """jsloc INTEGER,"""
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


def get_etag(ext_id, datepath, con, verbose, indent):
    txt = ""

    # Trying to parse etag file
    etagpath = next(
        iter(glob.glob(os.path.join(datepath, "*.crx.etag"))), None)
    if etagpath:
        with open(etagpath) as f:
            return f.read(), txt

    # Trying to parse header file for etag
    headerpath = next(
        iter(glob.glob(os.path.join(datepath, "*.crx.headers"))), None)
    if headerpath:
        with open(headerpath) as f:
            content = f.read()
            try:
                headers = eval(content)
                if "ETag" in headers:
                    return headers["ETag"], txt
            except Exception:
                txt = logmsg(
                    verbose, txt,
                    indent + "* WARNING: could not parse crx header file")
                pass

    # Trying to look up previous etag in database
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
                return row[0], txt

    return None, txt


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


def parse_and_insert_overview(ext_id, date, datepath, con, verbose, indent):
    txt = ""

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

            match = re.search(
                """<meta itemprop="ratingValue" content="(.*?)"\s*/>""",
                contents)
            rating = float(match.group(1)) if match else None

            match = re.search(
                """<meta itemprop="ratingCount" content="(.*?)"\s*/>""",
                contents)
            rating_count = int(match.group(1)) if match else None

            # Extracts extension categories
            match = re.search(
                """Attribute name="category">(.+?)</Attribute>""", contents)
            categories = match.group(1).split(",") if match else None

            # Extracts the number of downloads
            match = re.search(
                """<meta itemprop="interactionCount" content="UserDownloads:((:?\d|,)+)""",
                contents)
            downloads = int(match.group(1).replace(",", '')) if match else None

            # Extracts the full extension description as it appears on the
            # overview page
            doc = BeautifulSoup(contents, 'html.parser')

            description_parent = doc.find('div', itemprop="description")
            description = str(
                description_parent.contents[0]
            ) if description_parent and description_parent.contents else None
            full_description = str(
                description_parent.parent) if description_parent else None

            developer_parent = doc.find(
                class_=lambda cls: cls and "e-f-Me" in cls)
            developer = "".join([str(x) for x in developer_parent.contents
                                 ]) if developer_parent else None

            last_updated_parent = doc.find(
                class_=lambda cls: cls and "h-C-b-p-D-xh-hh" in cls)
            last_updated = str(last_updated_parent.contents[
                0]) if last_updated_parent else None

            etag, etag_msg = get_etag(ext_id, datepath, con, verbose, indent)
            txt = logmsg(verbose, txt, etag_msg)

            match = re.search(
                """<Attribute name="item_category">(.*?)</Attribute>""",
                contents)
            itemcategory = match.group(1) if match else None

            con.execute(
                "INSERT INTO extension VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (ext_id, date, name, version, description, downloads, rating,
                 rating_count, full_description, developer, itemcategory, etag,
                 last_updated))

            if categories:
                for category in categories:
                    con.execute("INSERT INTO category VALUES (?,?,?)",
                                (ext_id, date, category))

    return txt


def parse_and_insert_crx(ext_id, date, datepath, con, verbose, indent):
    txt = ""
    crx_path = next(iter(glob.glob(os.path.join(datepath, "*.crx"))), None)
    if crx_path:
        filename = os.path.basename(crx_path)

        with ZipFile(crx_path) as f:
            etag, etag_msg = get_etag(ext_id, datepath, con, verbose, indent)
            txt = logmsg(verbose, txt, etag_msg)
            with f.open("manifest.json") as m:
                raw_content = m.read()
                # There are some manifests that seem to have weird encodings...
                try:
                    content = raw_content.decode("utf-8-sig")
                except UnicodeDecodeError:
                    # Trying a different encoding, manifests are weird...
                    content = raw_content.decode("latin1")

                # Attempt to remove JavaScript-style comments from json
                comment_regex = re.compile(r'\s*//.*')
                multiline_comment_regex = re.compile(r'\s*/\\*.*\\*/')
                lines = content.splitlines()
                for index, line in enumerate(lines):
                    if comment_regex.match(
                            line) or multiline_comment_regex.match(line):
                        lines[index] = ""
                content = "\n".join(lines)

                manifest = json.loads(content, strict=False)
                if "permissions" in manifest:
                    for permission in manifest["permissions"]:
                        con.execute(
                            "INSERT OR REPLACE INTO permission VALUES (?,?)",
                            (etag, str(permission)))
                if "content_scripts" in manifest:
                    for csd in manifest["content_scripts"]:
                        if "matches" in csd:
                            for urlpattern in csd["matches"]:
                                con.execute(
                                    "INSERT OR REPLACE INTO content_script_url VALUES (?,?)",
                                    (etag, str(urlpattern)))

            size = os.path.getsize(crx_path)
            jsloc = 0
            jsfiles = filter(lambda x: x.filename.endswith(".js"),
                             f.infolist())
            for jsfile in jsfiles:
                with f.open(jsfile) as jsf:
                    content = jsf.read().decode(errors="surrogateescape")
                    beautified = jsbeautifier.beautify(content)
                    lines = beautified.splitlines()
                    jsloc += len(lines)

            public_key = read_crx(crx_path).pk

            con.execute("INSERT INTO crx VALUES (?,?,?,?,?)",
                        (etag, filename, size, jsloc, public_key))
    return txt


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


def update_sqlite_incremental(db_path, tmptardir, ext_id, date, verbose,
                              indent):
    txt = ""
    indent2 = indent + 4 * " "

    datepath = os.path.join(tmptardir, date)

    txt = logmsg(verbose, txt,
                 indent + "- updating with data from {}\n".format(date))

    if not os.path.exists(db_path):
        txt = logmsg(verbose, txt,
                     indent2 + "* db file does not exist, creating...\n")
        with SelfclosingSqliteDB(db_path) as con:
            setup_tables(con)

    with SelfclosingSqliteDB(db_path) as con:
        parse_and_insert_status(ext_id, date, datepath, con)

        parse_and_insert_overview(ext_id, date, datepath, con, verbose,
                                  indent2)

        etag, etag_msg = get_etag(ext_id, datepath, con, verbose, indent2)
        txt = logmsg(verbose, txt, etag_msg)
        etag_already_in_db = next(
            con.execute("SELECT COUNT(crx_etag) FROM crx WHERE crx_etag=?", (
                etag, )))[0]

        if etag:
            if not etag_already_in_db:
                try:
                    crx_msg = parse_and_insert_crx(ext_id, date, datepath, con,
                                                   verbose, indent)
                    txt = logmsg(verbose, txt, crx_msg)
                except zipfile.BadZipfile as e:
                    txt = logmsg(
                        verbose, txt, indent2 +
                        "* WARNING: the found crx file is not a zip file, exception: "
                    )
                    txt = logmsg(verbose, txt, str(e))
                    txt = logmsg(verbose, txt, "\n")
        else:
            crx_status = get_crx_status(datepath)
            if crx_status != 401 and crx_status != 204 and crx_status != 404:
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
