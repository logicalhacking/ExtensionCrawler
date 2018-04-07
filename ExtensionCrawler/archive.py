#!/usr/bin/env python3.6
#
# Copyright (C) 2016,2017 The University of Sheffield, UK
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
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
"""
Module for handling archives of the Browser Extension Crawler.
"""

import os
import glob
import re
import json
from concurrent.futures import TimeoutError
from pebble import ProcessPool, ProcessExpired
from functools import partial
import shutil
import tempfile
import time
import traceback
import tarfile
import datetime
import dateutil
import dateutil.parser
import requests

from ExtensionCrawler.config import (
    const_review_payload, const_review_search_url, const_download_url,
    get_local_archive_dir, const_overview_url, const_support_url,
    const_support_payload, const_review_search_payload, const_review_url)
from ExtensionCrawler.util import google_dos_protection, value_of, log_info, log_exception
from ExtensionCrawler.db import update_db_incremental


class Error(Exception):
    pass


class CrawlError(Error):
    def __init__(self, extid="", message="", pagecontent=""):
        self.extid = extid
        self.message = message
        self.pagecontent = pagecontent
        super(CrawlError, self).__init__()


class RequestResult:
    def __init__(self, response=None, exception=None):
        if response is not None:
            self.http_status = response.status_code
        self.exception = exception

    def is_ok(self):
        return (self.exception is None) and (self.http_status == 200)

    def not_authorized(self):
        return (self.exception is None) and (self.http_status == 401)

    def not_found(self):
        return (self.exception is None) and (self.http_status == 404)

    def has_exception(self):
        return self.exception is not None

    def not_available(self):
        return (self.exception is None) and (self.http_status == 503)

    def not_modified(self):
        return (self.exception is None) and (self.http_status == 304)


class UpdateResult:
    def __init__(self, id, is_new, exception, res_overview, res_crx,
                 res_reviews, res_support, res_sql, sql_update):
        self.id = id
        self.new = is_new
        self.exception = exception
        self.res_overview = res_overview
        self.res_crx = res_crx
        self.res_reviews = res_reviews
        self.res_support = res_support
        self.res_sql = res_sql
        self.sql_update = sql_update

    def is_new(self):
        return self.new

    def is_ok(self):
        return (self.res_overview.is_ok()
                and (self.res_crx.is_ok() or self.res_crx.not_modified())
                and ((self.res_reviews is None) or self.res_reviews.is_ok())
                and ((self.res_support is None) or self.res_support.is_ok()))

    def not_authorized(self):
        return (self.res_overview.not_authorized()
                or self.res_crx.not_authorized()
                or (self.res_reviews is not None
                    and self.res_reviews.not_authorized())
                or (self.res_support is not None
                    and self.res_support.not_authorized()))

    def not_in_store(self):
        return (self.res_overview.not_found() or self.res_crx.not_found() or
                (self.res_reviews is not None and self.res_reviews.not_found())
                or (self.res_support is not None
                    and self.res_support.not_found()))

    def has_exception(self):
        return (self.res_overview.has_exception()
                or self.res_crx.has_exception()
                or (self.res_reviews is not None
                    and self.res_reviews.has_exception())
                or (self.res_support is not None
                    and self.res_support.has_exception()))

    def raised_google_ddos(self):
        return ((self.res_reviews is not None
                 and self.res_reviews.not_available())
                or (self.res_support is not None
                    and self.res_support.not_available()))

    def not_modified(self):
        return self.res_crx.not_modified()

    def corrupt_tar(self):
        return self.exception is not None

    def sql_exception(self):
        return self.res_sql is not None

    def sql_success(self):
        return self.sql_update


def write_text(tardir, date, fname, text):
    directory = os.path.join(tardir, date)
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, fname), 'w') as f:
        f.write(text)


def store_request_metadata(tar, date, fname, request):
    write_text(tar, date, fname + ".headers", str(request.headers))
    write_text(tar, date, fname + ".status", str(request.status_code))
    write_text(tar, date, fname + ".url", str(request.url))


def store_request_text(tar, date, fname, request):
    write_text(tar, date, fname, request.text)
    store_request_metadata(tar, date, fname, request)


def httpdate(dt):
    weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday()]
    month = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct",
        "Nov", "Dec"
    ][dt.month - 1]
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekday, dt.day, month,
                                                    dt.year, dt.hour,
                                                    dt.minute, dt.second)


def last_modified_utc_date(path):
    if path is "":
        return ""
    return os.path.split(os.path.dirname(path))[1]


def last_modified_http_date(path):
    if path is "":
        return ""
    return httpdate(dateutil.parser.parse(last_modified_utc_date(path)))


def last_crx(archivedir, extid, date=None):
    last_crx = ""
    last_crx_etag = ""
    tar = os.path.join(archivedir, get_local_archive_dir(extid),
                       extid + ".tar")
    if os.path.exists(tar):
        with tarfile.open(tar, 'r') as t:
            old_crxs = sorted([
                x.name for x in t.getmembers()
                if x.name.endswith(".crx") and x.size > 0 and (
                    date is None or (dateutil.parser.parse(
                        os.path.split(os.path.split(x.name)[0])[1]) <= date))
            ])
            if old_crxs != []:
                last_crx = old_crxs[-1]
                headers_content = t.extractfile(
                    last_crx + ".headers").read().decode().replace(
                        '"', '\\"').replace("'", '"')
                headers_json = json.loads(headers_content)
                last_crx_etag = headers_json["ETag"]

    return last_crx, last_crx_etag


def first_crx(archivedir, extid, date=None):
    first_crx = ""
    tar = os.path.join(archivedir, get_local_archive_dir(extid),
                       extid + ".tar")
    if os.path.exists(tar):
        t = tarfile.open(tar, 'r')
        old_crxs = sorted([
            x.name for x in t.getmembers()
            if x.name.endswith(".crx") and x.size > 0 and (
                date is None or (date <= dateutil.parser.parse(
                    os.path.split(os.path.split(x.name)[0])[1])))
        ])
        t.close()
        if old_crxs != []:
            first_crx = old_crxs[0]

    return first_crx


def all_crx(archivedir, extid, date=None):
    tar = os.path.join(archivedir, get_local_archive_dir(extid),
                       extid + ".tar")
    all_crxs = []
    if os.path.exists(tar):
        t = tarfile.open(tar, 'r')
        all_crxs = sorted([
            x.name for x in t.getmembers()
            if x.name.endswith(".crx") and x.size > 0
        ])
        t.close()
    return all_crxs


def update_overview(tar, date, ext_id):
    res = None
    try:
        res = requests.get(const_overview_url(ext_id), timeout=10)
        log_info("* overview page: {}".format(str(res.status_code)), 2, ext_id)
        store_request_text(tar, date, 'overview.html', res)
    except Exception as e:
        log_exception("Exception when retrieving overview page", 2, ext_id)
        write_text(tar, date, 'overview.html.exception',
                   traceback.format_exc())
        return RequestResult(res, e)
    return RequestResult(res)


def validate_crx_response(res, extid, extfilename):
    regex_extfilename = re.compile(r'^extension[_0-9]+\.crx$')
    if not 'Content-Type' in res.headers:
        raise CrawlError(extid, 'Did not find Content-Type header.', '\n'.join(
            res.iter_lines()))
    if not res.headers['Content-Type'] == 'application/x-chrome-extension':
        text = [line.decode('utf-8') for line in res.iter_lines()]
        raise CrawlError(
            extid,
            'Expected Content-Type header to be application/x-chrome-extension, but got {}.'.
            format(res.headers['Content-Type']), '\n'.join(text))
    if not regex_extfilename.match(extfilename):
        raise CrawlError(
            extid, '{} is not a valid extension file name, skipping...'.format(
                extfilename))


def update_crx(archivedir, tmptardir, ext_id, date):
    res = None
    extfilename = "default_ext_archive.crx"
    last_crx_file, last_crx_etag = last_crx(archivedir, ext_id)
    last_crx_http_date = last_modified_http_date(last_crx_file)
    headers = ""
    if last_crx_file is not "":
        headers = {'If-Modified-Since': last_crx_http_date}
    try:
        log_info("* Checking If-Modified-Since")
        res = requests.get(
            const_download_url().format(ext_id),
            stream=True,
            headers=headers,
            timeout=10)
        log_info("* crx archive (Last: {}): {}".format(
            value_of(last_crx_http_date, "n/a"), str(res.status_code)), 2,
                 ext_id)
        extfilename = os.path.basename(res.url)
        if re.search('&', extfilename):
            extfilename = "default.crx"

        if res.status_code == 304:
            etag = requests.head(
                const_download_url().format(ext_id),
                timeout=10,
                allow_redirects=True).headers.get('ETag')
            write_text(tmptardir, date, extfilename + ".etag", etag)
            log_info("- checking etag, last: {}".format(last_crx_etag), 3,
                     ext_id)
            log_info("              current: {}".format(etag), 3, ext_id)

            if (etag is not "") and (etag != last_crx_etag):
                log_info("- downloading due to different etags", 3, ext_id)

                res = requests.get(
                    const_download_url().format(ext_id),
                    stream=True,
                    timeout=10)
            else:
                write_text(tmptardir, date, extfilename + ".link",
                           os.path.join("..",
                                        last_modified_utc_date(last_crx_file),
                                        extfilename) + "\n")
        store_request_metadata(tmptardir, date, extfilename, res)
        if res.status_code == 200:
            validate_crx_response(res, ext_id, extfilename)
            with open(os.path.join(tmptardir, date, extfilename), 'wb') as f:
                for chunk in res.iter_content(chunk_size=512 * 1024):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
            write_text(tmptardir, date, extfilename + ".etag",
                       res.headers.get("ETag"))
    except Exception as e:
        log_exception("Exception when updating crx", 3, ext_id)
        write_text(tmptardir, date, extfilename + ".exception",
                   traceback.format_exc())
        return RequestResult(res, e)
    return RequestResult(res)


def iterate_authors(pages):
    for page in pages:
        json_page = json.loads(page[page.index("{\""):page.rindex("}}},") + 1])
        for annotation in json_page["annotations"]:
            if "attributes" in annotation and "replyExists" in annotation["attributes"] and annotation["attributes"]["replyExists"]:
                yield (annotation["entity"]["author"],
                       annotation["entity"]["groups"])


def update_reviews(tar, date, ext_id):
    res = None
    try:
        pages = []

        # google_dos_protection()
        res = requests.post(
            const_review_url(),
            data=const_review_payload(ext_id, "0", "100"),
            timeout=10)
        log_info("* review page   0-100: {}".format(str(res.status_code)), 2,
                 ext_id)
        store_request_text(tar, date, 'reviews000-099.text', res)
        pages += [res.text]

        google_dos_protection()
        res = requests.post(
            const_review_url(),
            data=const_review_payload(ext_id, "100", "100"),
            timeout=10)
        log_info("* review page   100-200: {}".format(str(res.status_code)), 2,
                 ext_id)
        store_request_text(tar, date, 'reviews100-199.text', res)
        pages += [res.text]

        google_dos_protection()
        # Always start with reply number 0 and request 10 replies
        ext_id_author_tups = [(ext_id, author, 0, 10, groups)
                              for author, groups in iterate_authors(pages)]
        if ext_id_author_tups:
            res = requests.post(
                const_review_search_url(),
                data=const_review_search_payload(ext_id_author_tups),
                timeout=10)
            log_info("* review page replies: {}".format(str(res.status_code)),
                     2, ext_id)
            store_request_text(tar, date, 'reviewsreplies.text', res)
    except Exception as e:
        log_exception("Exception when updating reviews", 2, ext_id)
        write_text(tar, date, 'reviews.html.exception', traceback.format_exc())
        return RequestResult(res, e)
    return RequestResult(res)


def update_support(tar, date, ext_id):
    res = None
    try:
        pages = []

        google_dos_protection()
        res = requests.post(
            const_support_url(),
            data=const_support_payload(ext_id, "0", "100"),
            timeout=10)
        log_info("* support page   0-100: {}".format(str(res.status_code)), 2,
                 ext_id)
        store_request_text(tar, date, 'support000-099.text', res)
        pages += [res.text]

        google_dos_protection()
        res = requests.post(
            const_support_url(),
            data=const_support_payload(ext_id, "100", "100"),
            timeout=10)
        log_info("* support page 100-200: {}".format(str(res.status_code)), 2,
                 ext_id)
        store_request_text(tar, date, 'support100-199.text', res)
        pages += [res.text]

        google_dos_protection()
        # Always start with reply number 0 and request 10 replies
        ext_id_author_tups = [(ext_id, author, 0, 10, groups)
                              for author, groups in iterate_authors(pages)]
        if ext_id_author_tups:
            res = requests.post(
                const_review_search_url(),
                data=const_review_search_payload(ext_id_author_tups),
                timeout=10)
            log_info("* support page replies: {}".format(str(res.status_code)),
                     2, ext_id)
            store_request_text(tar, date, 'supportreplies.text', res)
    except Exception as e:
        log_exception("Exception when updating support pages", 2, ext_id)
        write_text(tar, date, 'support.html.exception', traceback.format_exc())
        return RequestResult(res, e)
    return RequestResult(res)


def update_extension(archivedir, forums, ext_id):
    log_info("Updating extension {}".format(" (including forums)"
                                            if forums else ""), 1, ext_id)
    is_new = False
    tar_exception = None
    sql_exception = None
    sql_success = False
    tmptardir = ""
    start = time.time()

    date = datetime.datetime.now(datetime.timezone.utc).isoformat()

    tardir = os.path.join(archivedir, get_local_archive_dir(ext_id), ext_id)
    tar = (tardir + ".tar")

    try:
        tmpdir = tempfile.mkdtemp()
        tmptardir = os.path.join(tmpdir, ext_id)
        log_info("* tmptardir = {}".format(tmptardir), 2, ext_id)
        os.makedirs(
            os.path.join(archivedir, get_local_archive_dir(ext_id)),
            exist_ok=True)
    except Exception as e:
        log_exception("* FATAL: cannot create tmpdir", 3, ext_id)
        tar_exception = e
        return UpdateResult(ext_id, is_new, tar_exception, None, None, None,
                            None, sql_exception, False)

    res_overview = update_overview(tmptardir, date, ext_id)
    res_reviews = None
    res_support = None
    if forums:
        res_reviews = update_reviews(tmptardir, date, ext_id)

    res_crx = update_crx(archivedir, tmptardir, ext_id, date)

    if forums:
        res_support = update_support(tmptardir, date, ext_id)

    backup = False
    if backup:
        try:
            os.sync()
            if os.path.exists(tardir + "bak.tar"):
                shutil.move(tardir + ".bak.tar",
                            tardir + ".bak." + date + ".tar")
                os.remove(tardir + ".bak." + date + ".tar")
        except Exception:
            pass

        try:
            if os.path.exists(tar):
                shutil.copyfile(tar, tardir + ".bak.tar")
        except Exception as e:
            log_exception("* FATAL: cannot rename old tar archive", 3, ext_id)
            tar_exception = e
            try:
                write_text(tardir, date, ext_id + ".tar.rename.exception",
                           traceback.format_exc())
            except Exception:
                pass

    if not os.path.exists(tar):
        is_new = True
    try:
        with tarfile.open(tar, mode='a:') as ar:
            ar.add(tmptardir, arcname=ext_id)
    except Exception as e:
        log_exception("* FATAL: cannot create tar archive", 3, ext_id)
        tar_exception = e
        try:
            write_text(tardir, date, ext_id + ".tar.create.exception",
                       traceback.format_exc())
        except Exception:
            pass

    try:
        update_db_incremental(tmptardir, ext_id, date)
        sql_success = True
    except Exception as e:
        log_exception("* Exception during update of db", 3, ext_id)
        sql_exception = e

        try:
            write_text(tardir, date, ext_id + ".sql.exception",
                       traceback.format_exc())
        except Exception as e:
            pass
    try:
        shutil.rmtree(path=tmpdir)
    except Exception as e:
        log_exception("* FATAL: cannot remove archive directory", 3, ext_id)
        tar_exception = e
        try:
            write_text(tardir, date, ext_id + ".dir.remove.exception",
                       traceback.format_exc())
        except Exception:
            pass

    log_info(
        "* Duration: {}".format(
            datetime.timedelta(seconds=int(time.time() - start))),
        2,
        ext_id)
    return UpdateResult(ext_id, is_new, tar_exception, res_overview, res_crx,
                        res_reviews, res_support, sql_exception, sql_success)


def execute_parallel(archivedir, max_retry, timeout, max_workers, ext_ids):
    results=[]
    for n in range(max_retry):
        if n > 0:
            log_info("Attempt ({} out of {}): {} extensions excluding forums (parallel)".format(
                n,max_retry,len(ext_timeouts)), 1)
            ext_ids=ext_timeouts

        ext_timeouts=[]   
        with ProcessPool(max_workers=max_workers, max_tasks=100) as pool:
            future = pool.map(partial(update_extension, archivedir, False)
                              ,ext_ids
                              ,timeout=timeout)
        # wait for pool is finished before processing results.
        iterator = future.result()
        ext_timeouts=[]
        for ext_id in ext_ids:
            try:
                results.append(next(iterator))
            except StopIteration:
                break
            except TimeoutError as error:
                log_info("WorkerException: Processing of %s took longer than %d seconds" % (ext_id,error.args[1]))
                ext_timeouts.append(ext_id)
                results.append(UpdateResult(ext_id, False, error,
                                            None, None, None,
                                            None, None, False))
            except ProcessExpired as error:
                log_info("WorkerException: %s (%s)self. Exit code: %d" % (error, ext_id, error.exitcode))
                ext_timeouts.append(ext_id)
                results.append(UpdateResult(ext_id, False, error,
                                            None, None, None,
                                            None, None, False))
            except Exception as error:
                log_info("WorkerException: Processing %s raised %s" % (ext_id, error))
                log_info(error.traceback)  # Python's traceback of remote process
                ext_timeouts.append(ext_id)
                results.append(UpdateResult(ext_id, False, error,
                                            None, None, None,
                                            None, None, False))
                    
    return results


def update_extensions(archivedir, parallel, forums_ext_ids, ext_ids, timeout=300):
    ext_with_forums = []
    ext_without_forums = []
    forums_ext_ids = (list(set(forums_ext_ids)))
    log_info("Updating {} extensions ({} including forums)".format(
        len(ext_ids), len(forums_ext_ids)))

    # First, update all extensions without forums in parallel (increased speed).
    # parallel_ids = list(set(ext_ids) - set(forums_ext_ids))
    parallel_ids = ext_ids
    log_info("Updating {} extensions excluding forums (parallel)".format(
        len(parallel_ids)), 1)
    ext_without_forums = execute_parallel(archivedir,3, timeout, parallel, parallel_ids)

    # Second, update extensions with forums sequentially (and with delays) to
    # avoid running into Googles DDOS detection.
    log_info("Updating {} extensions including forums (sequentially)".format(
        len(forums_ext_ids)), 1)
    ext_with_forums = execute_parallel(archivedir, 3, timeout, 1, forums_ext_ids)
                     
    return ext_with_forums + ext_without_forums


def get_existing_ids(archivedir):
    byte = '[0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z][0-9a-z]'
    word = byte + byte + byte + byte
    return list(
        map(lambda d: re.sub(".tar$", "", re.sub(r"^.*\/", "", d)),
            glob.glob(os.path.join(archivedir, "*", word + ".tar"))))


def get_forum_ext_ids(confdir):
    with open(os.path.join(confdir, "forums.conf")) as f:
        ids = f.readlines()
    r = re.compile('^[a-p]+$')
    ids = [x.strip() for x in ids]
    return list(filter(r.match, ids))
