#!/usr/bin/env python3
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


from pathlib import Path
import sqlite3
import re
from bs4 import BeautifulSoup
from zipfile import ZipFile
import json


def setup_tables(con):
    # TODO: delete old db if schemas don't match
    con.execute("""CREATE TABLE IF NOT EXISTS review ("""
                """id INTEGER PRIMARY KEY,"""
                """extid TEXT,"""
                """date TEXT,"""
                """user TEXT,"""
                """reviewdate TEXT,"""
                """rating TEXT,"""
                """comment TEXT"""
                """)""")
    con.execute("""CREATE TABLE IF NOT EXISTS category ("""
                """extid TEXT,"""
                """date TEXT,"""
                """category TEXT,"""
                """PRIMARY KEY (extid, date, category)"""
                """)""")
    con.execute("""CREATE TABLE IF NOT EXISTS permission ("""
                """crx_etag TEXT,"""
                """permission TEXT,"""
                """PRIMARY KEY (crx_etag, permission)"""
                """)""")
    con.execute("""CREATE TABLE IF NOT EXISTS crx ("""
                """etag TEXT PRIMARY KEY,"""
                """filename TEXT,"""
                """publickey BLOB"""
                """)""")
    con.execute("""CREATE TABLE IF NOT EXISTS extension ("""
                """extid TEXT,"""
                """date TEXT,"""
                """name TEXT,"""
                """version TEXT,"""
                """description TEXT,"""
                """downloads INTEGER,"""
                """fulldescription TEXT,"""
                """developer TEXT,"""
                """crx_etag TEXT,"""
                """PRIMARY KEY (extid, date),"""
                """FOREIGN KEY (crx_etag) REFERENCES crx(etag)"""
                """)""")

def get_etag(date, tmptardir):
    header_path = list((tmptardir / date).glob("*.crx.headers"))[0]

    with open(header_path) as f:
        return eval(f.read())["ETag"]

def parse_and_insert_overview(ext_id, date, tmptardir, con):
    overview_path = tmptardir / date / "overview.html"
    with open(overview_path) as overview_file:
        contents = overview_file.read()

        # Extract extension name
        match = re.search("""<meta itemprop="name" content="(.*?)"\s*/>""", contents)
        name = match.group(1) if match else None

        # Extract extension version
        match = re.search("""<meta itemprop="version" content="(.*?)"\s*/>""", contents)
        version = match.group(1) if match else None

        # Extract the short extension description as it appears on the overview page
        match = re.search("""<meta property="og:description" content="(.*?)"><meta""", contents)
        description = match.group(1) if match else None

        # Extracts extension categories
        match = re.search("""Attribute name="category">(.+?)</Attribute>""", contents)
        categories = match.group(1).split(",") if match else None

        # Extracts the number of downloads
        match = re.search("""user_count.*?(\d+)""", contents)
        downloads = int(match.group(1)) if match else None

        # Extracts the full extension description as it appears on the overview page
        doc = BeautifulSoup(contents, 'html.parser')

        desc = doc.find('div', itemprop="description")
        full_description = desc.parent if desc and desc.parent else None

        developer = doc.find(class_=lambda cls: cls and "e-f-Me" in cls)

        etag = get_etag(date, tmptardir)

        con.execute("INSERT INTO extension VALUES (?,?,?,?,?,?,?,?,?)",
                    (ext_id, date, name, version, description, downloads,
                     str(full_description), str(developer), etag))

        for category in categories:
            con.execute("INSERT INTO category VALUES (?,?,?)",
                        (ext_id, date, category))


def parse_and_insert_crx(ext_id, date, tmptardir, con):
    crx_path = list((tmptardir / date).glob("*.crx"))[0]
    filename = crx_path.name

    etag = get_etag(date, tmptardir)

    with ZipFile(str(crx_path)) as f:
        with f.open("manifest.json") as m:
            try:
                # There are some manifests that seem to have weird encodings...
                manifest = json.loads(m.read().decode("utf-8-sig"))
                if "permissions" in manifest:
                    for permission in manifest["permissions"]:
                        con.execute("INSERT INTO permission VALUES (?,?)",
                                    (etag, str(permission)))
            except json.decoder.JSONDecodeError:
                pass

        public_key = read_crx(str(crx_path)).pk

        con.execute("INSERT INTO crx VALUES (?,?,?)", (etag, filename, public_key))


def update_sqlite(archivedir, tmptardir, verbose, ext_id, date):
    tmptardir = Path(tmptardir)
    indent = 11 * " "

    txt = ""

    db_path = Path(archivedir) / ext_id[:3] / (ext_id + ".sqlite")
    txt = logmsg(verbose, txt, indent + 4 * " " + "- using db file {}\n".format(str(db_path)))

    with sqlite3.connect(str(db_path)) as con:
        setup_tables(con)
        parse_and_insert_overview(ext_id, date, tmptardir, con)

        etag = get_etag(date, tmptardir)
        etag_already_in_db = list(con.execute("SELECT COUNT(etag) FROM crx WHERE etag=?", (etag,)))[0][0]
        if not etag_already_in_db:
            txt = logmsg(verbose, txt, indent + 4 * " " + "- etag not found in db, parsing crx...")
            parse_and_insert_crx(ext_id, date, tmptardir, con)

        #TODO: add reviews

    return txt
