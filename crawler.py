#!/usr/bin/env python3
#
# Copyright (C) 2016 The University of Sheffield, UK
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
    #extension_list_url  = 'https://chrome.google.com/webstore/ajax/item?pv=20160822&count={}&category={}'
    detail_url = 'https://chrome.google.com/webstore/detail/{}'
    store_url = 'https://chrome.google.com/webstore'

    def __init__(self, basedir):
        self.basedir = basedir

    def download_extension(self, extid, extdir=""):
        extresult = requests.get(self.download_url.format(extid), stream=True)
        if extresult.status_code == 401:
            raise UnauthorizedError(extid)
        if not 'Content-Type' in extresult.headers:
            raise CrawlError(extid, 'Did not find Content-Type header.',
                             '\n'.join(extresult.iter_lines()))
        if not extresult.headers[
                'Content-Type'] == 'application/x-chrome-extension':
            raise CrawlError(
                extid,
                'Expected Content-Type header to be application/x-chrome-extension, but got {}.'.
                format(extresult.headers['Content-Type']),
                '\n'.join(extresult.iter_lines()))
        extfilename = os.path.basename(extresult.url)
        if not self.regex_extfilename.match(extfilename):
            raise CrawlError(
                extid,
                '{} is not a valid extension file name, skipping...'.format(
                    extfilename))
        with open(os.path.join(extdir, extfilename), 'wb') as f:
            for chunk in extresult.iter_content(chunk_size=512 * 1024):
                if chunk:  # filter out keep-alive new chunks
                    f.write(chunk)

    def download_storepage(self, extid, extdir):
        extpageresult = requests.get(self.detail_url.format(extid))
        with open(os.path.join(extdir, 'storepage.html'), 'w') as f:
            f.write(extpageresult.text)

    def handle_extension(self, extinfo, category=''):
        extid = extinfo[0]
        download_date = datetime.now(timezone.utc).isoformat()
        if not self.regex_extid.match(extid):
            raise CrawlError(extid,
                             '{} is not a valid extension id.\n'.format(extid))
        extdir = os.path.join(self.basedir, category, extid,download_date)
        if os.path.isdir(extdir):
            return False
        os.makedirs(extdir)

        # Write the extention metadata into a file
        with open(os.path.join(extdir, 'metadata.json'), 'w') as f:
            json.dump(extinfo, f, indent=5)

        self.download_storepage(extid, extdir)
        self.download_extension(extid, extdir)

        return True

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
                        '\rDownloading into {} ... {} of {} done ({} new ones)'.
                        format(
                            os.path.join(self.basedir, category), i,
                            len(extinfos), newExtensions))
                    sys.stdout.flush()
                    if self.handle_extension(extinfos[i], category):
                        newExtensions += 1
                except CrawlError as cerr:
                    sys.stdout.write('Error: {}\n'.format(cerr.message))
                    if cerr.pagecontent != "":
                        sys.stderr.write('Page content was:\n')
                        sys.stderr.write('{}\n'.format(cerr.pagecontent))
                except UnauthorizedError as uerr:
                    sys.stdout.write('Error: login needed\n')
            sys.stdout.write(
                '\rDownloading into {} ... {} of {} done ({} new ones)\n'.
                format(
                    os.path.join(self.basedir, category),
                    len(extinfos), len(extinfos), newExtensions))


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
        default='downloaded',
        help='The directory in which the downloaded extensions should be stored.'
    )

    args = parser.parse_args()
    crawler = ExtensionCrawler(args.dest)

    if args.interval:
        while True:
            for i in range(args.iterate):
                crawler.run(args.categories, args.nrexts)
                time.sleep(args.interval)
    else:
        for i in range(args.iterate):
            crawler.run(args.categories, args.nrexts)
