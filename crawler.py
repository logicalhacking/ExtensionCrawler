#!/usr/bin/env python3
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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import requests
import time
import sys
import os
import json
import re
import argparse
from datetime import datetime, timezone
datetime.now(timezone.utc).strftime("%Y%m%d")
import glob
import hashlib
import dateutil
import dateutil.parser
from random import randint
from time import sleep


class Error(Exception):
    pass


class StoreError(Error):
    def __init__(self, message, pagecontent=""):
        self.message = message
        self.pagecontent = pagecontent


class CrawlError(Error):
    def __init__(self, extid, message, pagecontent=""):
        self.extid = extid
        self.message = message
        self.pagecontent = pagecontent


class UnauthorizedError(Error):
    def __init__(self, extid):
        self.extid = extid


class ExtensionCrawler:
    possible_categories = [
        'extensions', 'ext/22-accessibility', 'ext/10-blogging',
        'ext/15-by-google', 'ext/11-web-development', 'ext/14-fun',
        'ext/6-news', 'ext/28-photos', 'ext/7-productivity',
        'ext/38-search-tools', 'ext/12-shopping', 'ext/1-communication',
        'ext/13-sports'
    ]
    regex_extid = re.compile(r'^[a-z]+$')
    regex_extfilename = re.compile(r'^extension[_0-9]+\.crx$')
    regex_store_date_string = re.compile(r'"([0-9]{8})"')

    download_url = 'https://clients2.google.com/service/update2/crx?response=redirect&nacl_arch=x86-64&prodversion=9999.0.9999.0&x=id%3D{}%26uc'
    extension_list_url = 'https://chrome.google.com/webstore/ajax/item?pv={}&count={}&category={}'
    detail_url = 'https://chrome.google.com/webstore/detail/{}'
    store_url = 'https://chrome.google.com/webstore'
    review_url = 'https://chrome.google.com/reviews/components'
    support_url = 'https://chrome.google.com/reviews/components'

    def __init__(self, basedir, verbose, weak, overview):
        self.basedir = basedir
        self.verbose = verbose
        self.weak_exists_check = weak
        self.google_dos_count = 0
        self.overview_only = overview

    def sha256(self, fname):
        hash_sha256 = hashlib.sha256()
        with open(fname, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
            return hash_sha256.hexdigest()

    def store_request_metadata(self, name, request):
        with open(name + ".headers", 'w') as f:
            f.write(str(request.headers))
        with open(name + ".status", 'w') as f:
            f.write(str(request.status_code))
        with open(name + ".url", 'w') as f:
            f.write(str(request.url))

    def google_dos_protection(self, name, request, max=3):
        if max >= 1:
            sleep(randint(1, max) * .5)

        if request.status_code == 503:
            if 0 < request.text.find('CAPTCHA'):
                print("    Warning: Captcha (" + name + ")")
                self.google_dos_count += 1
            else:
                print("    Warning: unknown status 503 (" + name + ")")

    def download_extension(self, extid, extdir="", last_download_date=""):
        if last_download_date != "":
            headers = {'If-Modified-Since': last_download_date}
            extresult = requests.get(self.download_url.format(extid),
                                     stream=True,
                                     headers=headers)
            if extresult.status_code == 304:
                if self.verbose:
                    print(
                        "    Not re-downloading (If-Modified-Since returned 304)"
                    )
                extfilename = os.path.basename(extresult.url)
                self.store_request_metadata(
                    os.path.join(extdir, extfilename), extresult)
                self.google_dos_protection(
                    os.path.join(extdir, extfilename), extresult)
                return False
        else:
            extresult = requests.get(self.download_url.format(extid),
                                     stream=True)

        extfilename = os.path.basename(extresult.url)
        self.store_request_metadata(
            os.path.join(extdir, extfilename), extresult)
        self.google_dos_protection(
            os.path.join(extdir, extfilename), extresult)

        if extresult.status_code == 401:
            raise UnauthorizedError(extid)
        if not 'Content-Type' in extresult.headers:
            raise CrawlError(extid, 'Did not find Content-Type header.',
                             '\n'.join(extresult.iter_lines()))
        if not extresult.headers[
                'Content-Type'] == 'application/x-chrome-extension':
            text = [line.decode('utf-8') for line in extresult.iter_lines()]
            raise CrawlError(
                extid,
                'Expected Content-Type header to be application/x-chrome-extension, but got {}.'.
                format(extresult.headers['Content-Type']), '\n'.join(text))
        if not self.regex_extfilename.match(extfilename):
            raise CrawlError(
                extid,
                '{} is not a valid extension file name, skipping...'.format(
                    extfilename))
        with open(os.path.join(extdir, extfilename), 'wb') as f:
            for chunk in extresult.iter_content(chunk_size=512 * 1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)
        return True

    def download_storepage(self, extid, extdir):
        extpageresult = requests.get(self.detail_url.format(extid))
        self.store_request_metadata(
            os.path.join(extdir, 'storepage.html'), extpageresult)
        self.google_dos_protection(
            os.path.join(extdir, 'storepage.html'), extpageresult, 0.1)
        with open(os.path.join(extdir, 'storepage.html'), 'w') as f:
            f.write(extpageresult.text)

    def download_support(self, extid, extdir):
        payload = (
            'req={{ "appId":94,' + '"version":"150922",' + '"hl":"en",' +
            '"specs":[{{"type":"CommentThread",' +
            '"url":"http%3A%2F%2Fchrome.google.com%2Fextensions%2Fpermalink%3Fid%3D{}",'
            + '"groups":"chrome_webstore_support",' + '"startindex":"{}",' +
            '"numresults":"{}",' + '"id":"379"}}],' + '"internedKeys":[],' +
            '"internedValues":[]}}')

        response = requests.post(
            self.support_url, data=payload.format(extid, "0", "100"))
        with open(os.path.join(extdir, 'support000-099.text'), 'w') as f:
            f.write(response.text)
        self.store_request_metadata(
            os.path.join(extdir, 'support000-099.text'), response)
        self.google_dos_protection(
            os.path.join(extdir, 'support000-099.text'), response)
        response = requests.post(
            self.support_url, data=payload.format(extid, "100", "100"))
        with open(os.path.join(extdir, 'support100-199.text'), 'w') as f:
            f.write(str(response.text))
        self.store_request_metadata(
            os.path.join(extdir, 'support100-199.text'), response)
        self.google_dos_protection(
            os.path.join(extdir, 'support100-199.text'), response)

    def download_reviews(self, extid, extdir):
        payload = (
            'req={{ "appId":94,' + '"version":"150922",' + '"hl":"en",' +
            '"specs":[{{"type":"CommentThread",' +
            '"url":"http%3A%2F%2Fchrome.google.com%2Fextensions%2Fpermalink%3Fid%3D{}",'
            + '"groups":"chrome_webstore",' + '"sortby":"cws_qscore",' +
            '"startindex":"{}",' + '"numresults":"{}",' + '"id":"428"}}],' +
            '"internedKeys":[],' + '"internedValues":[]}}')

        response = requests.post(
            self.review_url, data=payload.format(extid, "0", "100"))
        with open(os.path.join(extdir, 'reviews000-099.text'), 'w') as f:
            f.write(response.text)
        self.store_request_metadata(
            os.path.join(extdir, 'reviews000-099.text'), response)
        self.google_dos_protection(
            os.path.join(extdir, 'reviews000-099.text'), response)
        response = requests.post(
            self.review_url, data=payload.format(extid, "100", "100"))
        with open(os.path.join(extdir, 'reviews100-199.text'), 'w') as f:
            f.write(response.text)
        self.store_request_metadata(
            os.path.join(extdir, 'reviews100-199.text'), response)
        self.google_dos_protection(
            os.path.join(extdir, 'reviews100-199.text'), response)

    def httpdate(self, dt):
        weekday = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dt.weekday(
        )]
        month = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
            "Oct", "Nov", "Dec"
        ][dt.month - 1]
        return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (
            weekday, dt.day, month, dt.year, dt.hour, dt.minute, dt.second)

    def last_modified_date(self, path):
        utc = os.path.split(
            os.path.dirname(os.path.relpath(path, self.basedir)))[1]
        return self.httpdate(dateutil.parser.parse(utc))

    def update_extension(self,
                         extid,
                         overwrite,
                         extinfo=None,
                         cnt=None,
                         max_cnt=None):
        if not self.regex_extid.match(extid):
            raise CrawlError(extid,
                             '{} is not a valid extension id.\n'.format(extid))
        if self.verbose:
            if overwrite:
                sys.stdout.write("  Updating ")
            else:
                sys.stdout.write("  Downloading ")
            if cnt != None:
                sys.stdout.write("({}".format(cnt))
                if max_cnt != None:
                    sys.stdout.write("/{}".format(max_cnt))
                sys.stdout.write(") ".format(max_cnt))

            if self.overview_only:
                sys.stdout.write("overview page of ")
            else:
                sys.stdout.write("full data set of ")
            sys.stdout.write("extension {}\n".format(extid))

        download_date = datetime.now(timezone.utc).isoformat()
        extdir = os.path.join(self.basedir, extid, download_date)
        if (not overwrite
            ) and os.path.isdir(os.path.join(self.basedir, extid)):
            if self.verbose:
                print("    already archived")
            return False

        os.makedirs(extdir)

        self.download_storepage(extid, extdir)

        self.download_storepage(extid, extdir)
        if self.overview_only:
            return True

        old_archives = []
        for archive in glob.glob(self.basedir + "/" + extid + "/*/*.crx"):
            if os.path.isfile(archive):
                elem = (self.sha256(archive), archive)
                old_archives.append(elem)
        last_download_date = ""
        if self.weak_exists_check:
            if old_archives != []:
                last_download_date = self.last_modified_date((old_archives[-1]
                                                              )[1])

        if extinfo != None:
            with open(os.path.join(extdir, 'metadata.json'), 'w') as f:
                json.dump(extinfo, f, indent=5)

        self.download_reviews(extid, extdir)
        self.download_support(extid, extdir)

        download = self.download_extension(extid, extdir, last_download_date)

        if self.weak_exists_check and not download:
            cwd = os.getcwd()
            os.chdir(extdir)
            os.symlink("../" + os.path.relpath(old_archives[-1][1],
                                               self.basedir + "/" + extid),
                       os.path.basename(old_archives[-1][1]))
            os.chdir(cwd)

        else:
            for archive in glob.glob(extdir + "/*.crx"):
                same_files = [
                    x[1] for x in old_archives if x[0] == self.sha256(archive)
                ]
                if same_files != []:
                    os.rename(archive, archive + ".bak")
                    src = same_files[0]
                    cwd = os.getcwd()
                    os.chdir(extdir)
                    os.symlink("../" + os.path.relpath(src, self.basedir + "/"
                                                       + extid),
                               os.path.relpath(archive, extdir))
                    os.chdir(cwd)
                    os.remove(archive + ".bak")
                if self.verbose:
                    print("    download/update successful")

        return True

    def update_extension_list(self, extensions):
        n_attempts = 0
        n_success = 0
        n_login_required = 0
        n_errors = 0
        retry_extids = []
        for extid in extensions:
            try:
                n_attempts += 1
                self.update_extension(extid, True, None, n_attempts,
                                      len(extensions))
                n_success += 1
            except CrawlError as cerr:
                retry_extids.append(extid)
                sys.stdout.write('    Error: {}\n'.format(cerr.message))
                n_errors += 1
                if cerr.pagecontent != "":
                    sys.stderr.write('    Page content was:\n')
                    sys.stderr.write('    {}\n'.format(cerr.pagecontent))
            except UnauthorizedError as uerr:
                retry_extids.append(extid)
                sys.stdout.write('    Error: login needed\n')
                n_login_required += 1
            except ConnectionResetError as cerr:
                retry_extids.append(extid)
                sys.stdout.write('    Error: {}\n'.format(str(cerr)))
                n_errors += 1

            sys.stdout.flush()
        if self.verbose:
            print("*** Summary: Updated {} of {} extensions successfully".
                  format(n_success, n_attempts))
            print("***          Login required: {}".format(n_login_required))
            print("***          Hit Google DOS protection: {}".format(
                self.google_dos_count))
            print("***          Other Erros: {}".format(n_errors))
            sys.stdout.flush()
        return retry_extids

    def update_extensions(self):
        extensions = os.listdir(self.basedir)
        retry = self.update_extension_list(extensions)
        if retry != []:
            sys.stdout.write('\n\n')
            sys.stdout.write('Re-trying failed downloads ... \n')
            sys.stdout.flush()
            self.update_extension_list(retry)

    def handle_extension(self, extinfo):
        extid = extinfo[0]
        return self.update_extension(extid, False, extinfo)

    def get_store_date_string(self):
        response = requests.get(self.store_url).text
        match = re.search(self.regex_store_date_string, response)
        if not match:
            raise StoreError(
                'Could not find the date string in the response from {}.'.
                format(self.store_url), response)
        return match.group(1)

    def run(self, categories, nrExtensions):
        date_string = self.get_store_date_string()
        for category in categories:
            response = requests.post(
                self.extension_list_url.format(date_string, nrExtensions,
                                               category)).text
            bigjson = json.loads(response.lstrip(")]}'\n"))
            extinfos = bigjson[1][1]

            newExtensions = 0
            for i in range(len(extinfos)):
                extid = extinfos[i][0]
                try:
                    sys.stdout.write(
                        '\rDownloading ({}) into \"{}\" ... {} of {} done ({} new ones)'.
                        format(category,
                               os.path.join(self.basedir), i,
                               len(extinfos), newExtensions))
                    sys.stdout.flush()
                    if self.verbose:
                        sys.stdout.write("\n")
                    if self.handle_extension(extinfos[i]):
                        newExtensions += 1
                except CrawlError as cerr:
                    sys.stdout.write('Error: {}\n'.format(cerr.message))
                    if cerr.pagecontent != "":
                        sys.stderr.write('Page content was:\n')
                        sys.stderr.write('{}\n'.format(cerr.pagecontent))
                except UnauthorizedError as uerr:
                    sys.stdout.write('Error: login needed\n')
            sys.stdout.write(
                '\rDownloading ({}) into {} ... {} of {} done ({} new ones)\n'.
                format(category,
                       os.path.join(self.basedir),
                       len(extinfos), len(extinfos), newExtensions))
            sys.stdout.flush()
            if self.verbose:
                sys.stdout.write("\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Downloads extensions from the Chrome Web Store.')
    parser.add_argument(
        '-t',
        '--interval',
        nargs='?',
        const=5,
        type=int,
        help='Keep downloading extensions every X seconds.')
    parser.add_argument(
        '-i',
        '--iterate',
        metavar='i',
        default=1,
        type=int,
        help='Queries the store i times for a list of extensions.')
    parser.add_argument(
        '-n',
        '--nrexts',
        metavar='N',
        default=200,
        type=int,
        help='The number of extensions to be downloaded per request (Google does not accept values much higher than 200).'
    )
    parser.add_argument(
        '-c',
        '--categories',
        nargs='*',
        default=ExtensionCrawler.possible_categories,
        choices=ExtensionCrawler.possible_categories,
        help='Only download extensions from the specified categories.')
    parser.add_argument(
        '-d',
        '--dest',
        default='archive',
        help='The directory in which the downloaded extensions should be stored.'
    )
    parser.add_argument(
        '--discover',
        action='store_true',
        help='Discover new extensions (default: only updated already downloaded extensions).'
    )
    parser.add_argument(
        '-v', '--verbose', action='store_true', help='Increase verbosity.')
    parser.add_argument(
        '-o',
        '--overview',
        action='store_true',
        help='Only download/update overview page.')
    parser.add_argument(
        '-w',
        '--weak',
        action='store_true',
        help='weak check if crx exists already')

    args = parser.parse_args()
    crawler = ExtensionCrawler(args.dest, args.verbose, args.weak,
                               args.overview)

    if args.discover:
        if args.interval:
            while True:
                for i in range(args.iterate):
                    crawler.run(args.categories, args.nrexts)
                    time.sleep(args.interval)
        else:
            for i in range(args.iterate):
                crawler.run(args.categories, args.nrexts)
    else:
        crawler.update_extensions()
