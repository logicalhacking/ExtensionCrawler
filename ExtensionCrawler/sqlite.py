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
from ExtensionCrawler.archive import *


from pathlib import Path
import sqlite3
import re
from bs4 import BeautifulSoup
from zipfile import ZipFile
import json
import os
import tempfile
import tarfile



def get_local_archive_dir(id):
    return "{}".format(id[:3])

def archive_file(archivedir,ext_id):
    return os.path.join(str(archivedir), get_local_archive_dir(ext_id),
                       ext_id + ".tar")



class IncrementalSqliteUpdateError(Exception):
    def __init__(self, reason="unknown"):
        self.reason = reason

def setup_tables(con):
    # TODO: delete old db if schemas don't match
    con.execute("""CREATE TABLE review ("""
                """id INTEGER PRIMARY KEY,"""
                """extid TEXT,"""
                """date TEXT,"""
                """user TEXT,"""
                """reviewdate TEXT,"""
                """rating TEXT,"""
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
                """crx_status INTEGER,"""
                """overview_status INTEGER,"""
                """lastupdated TEXT,"""
                """PRIMARY KEY (extid, date),"""
                """FOREIGN KEY (crx_etag) REFERENCES crx(etag)"""
                """)""")


def get_etag(datepath):
    etagpath = next(datepath.glob("*.etag"), None)

    if etagpath:
        with open(str(etagpath)) as f:
            return f.read()

def get_overview_status(datepath):
    with open(str(datepath / "overview.html.status")) as f:
       return int(f.read())

def get_crx_status(datepath):
    with open(str(next(datepath.glob("*.crx.status")))) as f:
        return int(f.read())

def parse_and_insert_overview(ext_id, date, datepath, con):
    overview_path = datepath / "overview.html"
    with open(str(overview_path)) as overview_file:
        contents = overview_file.read()

        # Extract extension name
        match = re.search("""<meta itemprop="name" content="(.*?)"\s*/>""", contents)
        name = match.group(1) if match else None

        # Extract extension version
        match = re.search("""<meta itemprop="version" content="(.*?)"\s*/>""", contents)
        version = match.group(1) if match else None

        # Extracts extension categories
        match = re.search("""Attribute name="category">(.+?)</Attribute>""", contents)
        categories = match.group(1).split(",") if match else None

        # Extracts the number of downloads
        match = re.search("""user_count.*?(\d+)""", contents)
        downloads = int(match.group(1)) if match else None

        # Extracts the full extension description as it appears on the overview page
        doc = BeautifulSoup(contents, 'html.parser')

        description_parent = doc.find('div', itemprop="description")
        description = str(description_parent.contents[0]) if description_parent and description_parent.contents else None
        full_description = str(description_parent.parent) if description_parent else None

        developer_parent = doc.find(class_=lambda cls: cls and "e-f-Me" in cls)
        developer = str(developer_parent.contents[0]) if developer_parent else None

        last_updated_parent = doc.find(class_=lambda cls: cls and "h-C-b-p-D-xh-hh" in cls)
        last_updated = str(last_updated_parent.contents[0]) if last_updated_parent else None

        etag = get_etag(datepath)

        overview_status = get_overview_status(datepath)

        crx_status = get_crx_status(datepath)


        con.execute("INSERT INTO extension VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (ext_id, date, name, version, description, downloads,
                     full_description, developer, etag, last_updated, overview_status, crx_status))

        if categories:
            for category in categories:
                con.execute("INSERT INTO category VALUES (?,?,?)",
                            (ext_id, date, category))


def parse_and_insert_crx(ext_id, date, datepath, con, verbose, indent):
    txt = ""

    etag = get_etag(datepath)
    crx_path = next(datepath.glob("*.crx"), None)
    filename = crx_path.name

    try:
        with ZipFile(str(crx_path)) as f:
            with f.open("manifest.json") as m:
                try:
                    # There are some manifests that seem to have weird encodings...
                    manifest = json.loads(m.read().decode("utf-8-sig"))
                    if "permissions" in manifest:
                        for permission in manifest["permissions"]:
                            con.execute("INSERT OR REPLACE INTO permission VALUES (?,?)",
                                        (etag, str(permission)))
                except json.decoder.JSONDecodeError:
                    pass

            public_key = read_crx(str(crx_path)).pk

            con.execute("INSERT INTO crx VALUES (?,?,?)", (etag, filename, public_key))
    except zipfile.BadZipFile as e:
        txt = logmsg(verbose, txt, indent + "- {} is not a zip file\n"
                        .format(crx_path))
    return txt


def update_sqlite_incremental(db_path, datepath, ext_id, date, verbose, indent):
    txt = ""

    txt = logmsg(verbose, txt, indent + "- updating using {}\n".format(datepath))

    if not db_path.exists():
        raise IncrementalSqliteUpdateError("db file not found")

    with sqlite3.connect(str(db_path)) as con:
        parse_and_insert_overview(ext_id, date, datepath, con)

        crx_path = next(datepath.glob("*.crx"), None)

        etag = get_etag(datepath)
        etag_already_in_db = next(con.execute("SELECT COUNT(etag) FROM crx WHERE etag=?", (etag,)))[0]
        if etag and not etag_already_in_db:
            if crx_path:
                parse_and_insert_crx(ext_id, date, datepath, con, verbose, indent)
            else:
                raise IncrementalSqliteUpdateError("etag not in db and no crx file present")

    return txt


def update_sqlite_full(db_path, archivedir, ext_id, verbose, indent):
    txt = ""

    if db_path.exists():
        os.remove(db_path)

    with tempfile.TemporaryDirectory() as tmpdir:
      tar = archive_file(archivedir,ext_id)
      with tarfile.open(tar) as t:
            t.extractall(tmpdir)
            iddir = Path(tmpdir) / ext_id

            with sqlite3.connect(str(db_path)) as con:
                setup_tables(con)
            for datepath in sorted(iddir.iterdir()):
                date = datepath.name
                updatetxt = update_sqlite_incremental(db_path, datepath, ext_id, date, verbose, indent)
                txt = logmsg(verbose, txt, updatetxt)

    return txt

def update_sqlite(archivedir, tmptardir, ext_id, date, verbose, indent):
    txt = ""

    datepath = Path(tmptardir) / date
    archivedir = Path(archivedir)
    indent2 = indent + 4 * " "


    txt = logmsg(verbose, txt, indent + "* extracting information into SQLite db...\n")

    db_path = Path(archivedir) / ext_id[:3] / (ext_id + ".sqlite")

    try:
        txt = logmsg(verbose, txt, indent2 + "- attempting incremental update...\n")
        updatetxt = update_sqlite_incremental(db_path, datepath, ext_id, date, verbose, indent2)
        txt = logmsg(verbose, txt, updatetxt)
    except IncrementalSqliteUpdateError as e:
        txt = logmsg(verbose, txt, indent2 + "- incremental update failed: {}\n".format(e.reason))
        txt = logmsg(verbose, txt, indent2 + "- regenerating full db...\n")
        try:
            fullmsg = update_sqlite_full(db_path, archivedir, ext_id, verbose, indent2)
            txt = logmsg(verbose, txt, fullmsg)
        except IncrementalSqliteUpdateError as e:
            txt = logmsg(verbose, txt, indent2 + "- full sqlite update failed: {}, giving up\n".format(e.reason))

    return txt
