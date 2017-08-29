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
from ExtensionCrawler.js_decomposer import decompose_js, DetectionType, FileClassification

from ExtensionCrawler.dbbackend.sqlite_backend import SqliteBackend
from ExtensionCrawler.dbbackend.mysql_backend import MysqlBackend

import re
from bs4 import BeautifulSoup
from zipfile import ZipFile
import json
import os
import glob
import datetime
import logging


def get_etag(ext_id, datepath, con):
    # Trying to parse etag file
    etagpath = next(
        iter(glob.glob(os.path.join(datepath, "*.crx.etag"))), None)
    if etagpath:
        with open(etagpath) as f:
            return f.read()

    # Trying to parse header file for etag
    headerpath = next(
        iter(glob.glob(os.path.join(datepath, "*.crx.headers"))), None)
    if headerpath:
        with open(headerpath) as f:
            content = f.read()
            try:
                headers = eval(content)
                if "ETag" in headers:
                    return headers["ETag"]
            except Exception:
                logging.warning(16 * " " +
                                "* WARNING: could not parse crx header file")

    # Trying to look up previous etag in database
    linkpath = next(
        iter(glob.glob(os.path.join(datepath, "*.crx.link"))), None)
    if linkpath:
        with open(linkpath) as f:
            link = f.read()
            linked_date = link[3:].split("/")[0]

            result = con.get_most_recent_etag(ext_id,
                                              con.convert_date(linked_date))
            if result is not None:
                return result

    return None


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
    logging.info(16 * " " + "- parsing overview file")
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

            etag = get_etag(ext_id, datepath, con)

            match = re.search(
                """<Attribute name="item_category">(.*?)</Attribute>""",
                contents)
            itemcategory = match.group(1) if match else None

            con.insert(
                "extension",
                extid=ext_id,
                date=con.convert_date(date),
                name=name,
                version=version,
                description=description,
                downloads=downloads,
                rating=rating,
                ratingcount=rating_count,
                fulldescription=full_description,
                developer=developer,
                itemcategory=itemcategory,
                crx_etag=etag,
                lastupdated=last_updated)

            if categories:
                for category in categories:
                    con.insert(
                        "category",
                        extid=ext_id,
                        date=con.convert_date(date),
                        category=category)


def parse_and_insert_crx(ext_id, date, datepath, con):
    logging.info(16 * " " + "- parsing crx file")
    crx_path = next(iter(glob.glob(os.path.join(datepath, "*.crx"))), None)
    if crx_path:
        filename = os.path.basename(crx_path)

        with ZipFile(crx_path) as f:
            etag = get_etag(ext_id, datepath, con)

            size = os.path.getsize(crx_path)
            public_key = read_crx(crx_path).public_key

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
                multiline_comment_regex = re.compile(r'\s*/\\*.*\\*/\s*')
                lines = content.splitlines()
                for index, line in enumerate(lines):
                    if comment_regex.fullmatch(
                            line) or multiline_comment_regex.fullmatch(line):
                        lines[index] = ""
                content = "\n".join(lines)

                con.insert(
                    "crx",
                    crx_etag=etag,
                    filename=filename,
                    size=size,
                    manifest=content,
                    publickey=public_key)

                manifest = json.loads(content, strict=False)
                if "permissions" in manifest:
                    for permission in manifest["permissions"]:
                        con.insert(
                            "permission",
                            crx_etag=etag,
                            permission=str(permission))
                if "content_scripts" in manifest:
                    for csd in manifest["content_scripts"]:
                        if "matches" in csd:
                            for urlpattern in csd["matches"]:
                                con.insert(
                                    "content_script_url",
                                    crx_etag=etag,
                                    url=str(urlpattern))

            js_files = decompose_js(f)
            for js_file_info in js_files:
                # TODO: Add: evidenceStartPos, evidenceEndPos, and EvidenceText
                con.insert(
                    "jsfile",
                    crx_etag=etag,
                    detect_method=str(js_file_info['detectMethod']),
                    filename=js_file_info['jsFilename'],
                    type=(js_file_info['type']).name,
                    lib=js_file_info['lib'],
                    path=js_file_info['path'],
                    md5=js_file_info['md5'],
                    size=js_file_info['size'],
                    version=js_file_info['ver'])


def get(d, k):
    if d and k in d:
        return d[k]


def parse_and_insert_review(ext_id, date, reviewpath, con):
    logging.info(16 * " " + "- parsing review file")
    with open(reviewpath) as f:
        content = f.read()
        stripped = content[content.find('{"'):]
        d = json.JSONDecoder().raw_decode(stripped)
        annotations = get(next(iter(d), None), "annotations")
        if annotations:
            results = []
            for review in d[0]["annotations"]:
                results += [{
                    "extid":
                    ext_id,
                    "date":
                    con.convert_date(date),
                    "commentdate":
                    datetime.datetime.utcfromtimestamp(
                        get(review, "timestamp")).isoformat()
                    if "timestamp" in review else None,
                    "rating":
                    get(review, "starRating"),
                    "comment":
                    get(review, "comment"),
                    "displayname":
                    get(get(review, "entity"), "displayName"),
                    "author":
                    get(get(review, "entity"), "author"),
                    "language":
                    get(review, "language"),
                    "shortauthor":
                    get(get(review, "entity"), "shortAuthor")
                }]

            con.insertmany("review", results)


def parse_and_insert_support(ext_id, date, supportpath, con):
    logging.info(16 * " " + "- parsing support file")
    with open(supportpath) as f:
        content = f.read()
        stripped = content[content.find('{"'):]
        d = json.JSONDecoder().raw_decode(stripped)
        annotations = get(next(iter(d), None), "annotations")
        if annotations:
            results = []
            for review in d[0]["annotations"]:
                results += [{
                    "extid":
                    ext_id,
                    "date":
                    con.convert_date(date),
                    "commentdate":
                    datetime.datetime.utcfromtimestamp(
                        get(review, "timestamp")).isoformat()
                    if "timestamp" in review else None,
                    "title":
                    get(review, "title"),
                    "comment":
                    get(review, "comment"),
                    "displayname":
                    get(get(review, "entity"), "displayName"),
                    "author":
                    get(get(review, "entity"), "author"),
                    "language":
                    get(review, "language"),
                    "shortauthor":
                    get(get(review, "entity"), "shortAuthor")
                }]

            con.insertmany("support", results)


def parse_and_insert_replies(ext_id, date, repliespath, con):
    logging.info(16 * " " + "- parsing reply file")
    with open(repliespath) as f:
        d = json.load(f)
        if not "searchResults" in d:
            logging.warning("* WARNING: there are no search results in {}".
                            format(repliespath))
        results = []
        for result in d["searchResults"]:
            if "annotations" not in result:
                continue
            for annotation in result["annotations"]:
                results += [{
                    "extid":
                    ext_id,
                    "date":
                    con.convert_date(date),
                    "commentdate":
                    datetime.datetime.utcfromtimestamp(
                        get(annotation, "timestamp")).isoformat()
                    if "timestamp" in annotation else None,
                    "replyto":
                    get(
                        get(get(annotation, "entity"), "annotation"),
                        "author"),
                    "comment":
                    get(annotation, "comment"),
                    "displayname":
                    get(get(annotation, "entity"), "displayName"),
                    "author":
                    get(get(annotation, "entity"), "author"),
                    "language":
                    get(annotation, "language"),
                    "shortauthor":
                    get(get(annotation, "entity"), "shortAuthor")
                }]
        con.insertmany("reply", results)
    return ""


def parse_and_insert_status(ext_id, date, datepath, con):
    logging.info(16 * " " + "- parsing status file")
    overview_status = get_overview_status(datepath)
    crx_status = get_crx_status(datepath)

    overviewexceptionpath = os.path.join(datepath, "overview.html.exception")
    overview_exception = None
    if os.path.exists(overviewexceptionpath):
        with open(overviewexceptionpath) as f:
            overview_exception = f.read()

    con.insert(
        "status",
        extid=ext_id,
        date=con.convert_date(date),
        crx_status=crx_status,
        overview_status=overview_status,
        overview_exception=overview_exception)


def update_sqlite_incremental(db_path, tmptardir, ext_id, date):
    logging.info(12 * " " + "- parsing data from {}".format(date))
    datepath = os.path.join(tmptardir, date)

    if const_use_mysql():
        # Don't forget to create a ~/.my.cnf file with the credentials
        backend = MysqlBackend(read_default_file=const_mysql_config_file())
    else:
        backend = SqliteBackend(db_path)

    with backend as con:
        etag = get_etag(ext_id, datepath, con)

        if etag:
            try:
                parse_and_insert_crx(ext_id, date, datepath, con)
            except zipfile.BadZipfile as e:
                logging.warning(
                    16 * " " +
                    "* WARNING: the found crx file is not a zip file, exception: {}".
                    format(str(e)))
        else:
            crx_status = get_crx_status(datepath)
            if crx_status != 401 and crx_status != 204 and crx_status != 404:
                logging.warning(16 * " " + "* WARNING: could not find etag")

        parse_and_insert_overview(ext_id, date, datepath, con)
        parse_and_insert_status(ext_id, date, datepath, con)

        reviewpaths = glob.glob(os.path.join(datepath, "reviews*-*.text"))
        for reviewpath in reviewpaths:
            try:
                parse_and_insert_review(ext_id, date, reviewpath, con)
            except json.decoder.JSONDecodeError as e:
                logging.warning(16 * " " +
                                "* Could not parse review file, exception: {}".
                                format(str(e)))

        supportpaths = glob.glob(os.path.join(datepath, "support*-*.text"))
        for supportpath in supportpaths:
            try:
                parse_and_insert_support(ext_id, date, supportpath, con)
            except json.decoder.JSONDecodeError as e:
                logging.warning(
                    16 * " " + "* Could not parse support file, exception: {}".
                    format(str(e)))

        repliespaths = glob.glob(os.path.join(datepath, "*replies.text"))
        for repliespath in repliespaths:
            try:
                parse_and_insert_replies(ext_id, date, repliespath, con)
            except json.decoder.JSONDecodeError as e:
                logging.warning(16 * " " +
                                "* Could not parse reply file, exception: {}".
                                format(str(e)))
