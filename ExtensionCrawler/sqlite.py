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

from ExtensionCrawler import archive

import sqlite3
import re
from bs4 import BeautifulSoup
from zipfile import ZipFile
import json
import os
import tempfile
import tarfile
import glob


class SqliteUpdateError(Exception):
    def __init__(self, reason="unknown"):
        self.reason = reason


def get_etag(ext_id, datepath, con):
    #Trying etag file
    etagpath = next(iter(glob.glob(os.path.join(datepath, "*.etag"))), None)
    if etagpath:
        with open(etagpath) as f:
            return f.read()

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
    with open(os.path.join(datepath, "overview.html.status")) as f:
        return int(f.read())


def get_crx_status(datepath):
    statuspath = next(
        iter(glob.glob(os.path.join(datepath, "*.crx.status"))), None)
    if statuspath:
        with open(statuspath) as f:
            return int(f.read())


def parse_and_insert_overview(ext_id, date, datepath, con):
    overview_path = os.path.join(datepath, "overview.html")
    with open(overview_path) as overview_file:
        contents = overview_file.read()

        # Extract extension name
        match = re.search("""<meta itemprop="name" content="(.*?)"\s*/>""",
                          contents)
        name = match.group(1) if match else None

        # Extract extension version
        match = re.search("""<meta itemprop="version" content="(.*?)"\s*/>""",
                          contents)
        version = match.group(1) if match else None

        # Extracts extension categories
        match = re.search("""Attribute name="category">(.+?)</Attribute>""",
                          contents)
        categories = match.group(1).split(",") if match else None

        # Extracts the number of downloads
        match = re.search("""user_count.*?(\d+)""", contents)
        downloads = int(match.group(1)) if match else None

        # Extracts the full extension description as it appears on the overview page
        doc = BeautifulSoup(contents, 'html.parser')

        description_parent = doc.find('div', itemprop="description")
        description = str(description_parent.contents[
            0]) if description_parent and description_parent.contents else None
        full_description = str(
            description_parent.parent) if description_parent else None

        developer_parent = doc.find(class_=lambda cls: cls and "e-f-Me" in cls)
        developer = str(
            developer_parent.contents[0]) if developer_parent else None

        last_updated_parent = doc.find(
            class_=lambda cls: cls and "h-C-b-p-D-xh-hh" in cls)
        last_updated = str(
            last_updated_parent.contents[0]) if last_updated_parent else None

        etag = get_etag(ext_id, datepath, con)

        overview_status = get_overview_status(datepath)

        crx_status = get_crx_status(datepath)

        con.execute("INSERT INTO extension VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    (ext_id, date, name, version, description, downloads,
                     full_description, developer, etag, last_updated,
                     overview_status, crx_status))

        if categories:
            for category in categories:
                con.execute("INSERT INTO category VALUES (?,?,?)",
                            (ext_id, date, category))


def parse_and_insert_crx(ext_id, date, datepath, con):
    etag = get_etag(ext_id, datepath, con)
    crx_path = next(iter(glob.glob(os.path.join(datepath, "*.crx"))), None)
    filename = os.path.basename(crx_path)

    with ZipFile(crx_path) as f:
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


def update_sqlite_incremental(db_path, datepath, ext_id, date, verbose,
                              indent):
    txt = ""

    txt = logmsg(verbose, txt,
                 indent + "- updating using {}\n".format(datepath))

    if not os.path.exists(db_path):
        raise SqliteUpdateError("db file not found")

    with sqlite3.connect(db_path) as con:
        parse_and_insert_overview(ext_id, date, datepath, con)

        crx_path = next(iter(glob.glob(os.path.join(datepath, "*.crx"))), None)

        etag = get_etag(ext_id, datepath, con)
        etag_already_in_db = next(
            con.execute("SELECT COUNT(etag) FROM crx WHERE etag=?", (etag, )))[
                0]
        if etag and not etag_already_in_db:
            if crx_path:
                parse_and_insert_crx(ext_id, date, datepath, con)
            else:
                raise SqliteUpdateError(
                    "etag not in db and no crx file present")

    return txt


def update_sqlite(archivedir, tmptardir, ext_id, date, verbose, indent):
    update_successful = False
    txt = ""
    indent2 = indent + 4 * " "

    datepath = os.path.join(tmptardir, date)

    txt = logmsg(verbose, txt,
                 indent + "* extracting information into SQLite db...\n")

    db_path = os.path.join(archivedir, ext_id[:3], ext_id + ".sqlite")

    txt = logmsg(verbose, txt,
                 indent2 + "- attempting incremental update...\n")
    try:
        updatetxt = update_sqlite_incremental(db_path, datepath, ext_id, date,
                                              verbose, indent2)
        txt = logmsg(verbose, txt, updatetxt)
        update_successful = True
    except SqliteUpdateError as e:
        txt = logmsg(
            verbose, txt,
            indent2 + "- incremental update failed: {}\n".format(e.reason))

    return update_successful, txt
