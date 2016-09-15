#!/usr/bin/env python3
import requests
import time
import sys
import os
import json
import re
import argparse

class Error(Exception):
    pass

class CrawlError(Error):
    def __init__(self, extid, message, pagecontent=""):
        self.extid = extid
        self.message = message
        self.pagecontent = pagecontent

class UnauthorizedError(Error):
    def __init__(self, extid):
        self.extid = extid

class ExtensionCrawler:
    possible_categories = ['extensions', 'ext/22-accessibility', 'ext/10-blogging', 'ext/15-by-google', 'ext/11-web-development', 'ext/14-fun', 'ext/6-news', 'ext/28-photos', 'ext/7-productivity', 'ext/38-search-tools', 'ext/12-shopping', 'ext/1-communication', 'ext/13-sports']
    regexExtid       = re.compile(r'^[a-z]+$')
    regexExtfilename = re.compile(r'^extension[_0-9]+\.crx$')

    download_url      = 'https://clients2.google.com/service/update2/crx?response=redirect&nacl_arch=x86-64&prodversion=9999.0.9999.0&x=id%3D{}%26uc'
    extension_list_url = 'https://chrome.google.com/webstore/ajax/item?pv=20160822&count={}&category={}'
    detail_url        = 'https://chrome.google.com/webstore/detail/{}'

    def __init__(self, basedir):
        self.basedir = basedir

    def download_extension(self, extid, extdir=""):
        extresult = requests.get(self.download_url.format(extid), stream=True)
        if extresult.status_code == 401:
            raise UnauthorizedError(extid)
        if not 'Content-Type' in extresult.headers:
            raise CrawlError(extid, 'Did not find Content-Type header.', '\n'.join(extresult.iter_lines()))
        if not extresult.headers['Content-Type'] == 'application/x-chrome-extension':
            raise CrawlError(extid, 'Expected Content-Type header to be application/x-chrome-extension, but got {}.'.format(extresult.headers['Content-Type']), '\n'.join(extresult.iter_lines()))
        extfilename = os.path.basename(extresult.url)
        if not self.regexExtfilename.match(extfilename):
            raise CrawlError(extid, '{} is not a valid extension file name, skipping...'.format(extfilename))
        with open(os.path.join(extdir, extfilename), 'wb') as f:
            for chunk in extresult.iter_content(chunk_size=512 * 1024): 
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)

    def download_storepage(self, extid, extdir):
        extpageresult = requests.get(self.detail_url.format(extid))
        with open(os.path.join(extdir, 'storepage.html'), 'w') as f:
            f.write(extpageresult.text)

    def handle_extension(self, extinfo):
        extid = extinfo[0]
        if not self.regexExtid.match(extid):
            raise CrawlError(extid, '{} is not a valid extension id.\n'.format(extid))
        extdir = os.path.join(self.basedir, extid)
        if os.path.isdir(extdir):
            raise CrawlError(extid, '{} already exists'.format(extdir))
        os.makedirs(extdir)

        # Write the extention metadata into a file
        with open(os.path.join(extdir, 'metadata.json'), 'w') as f:
            json.dump(extinfo, f, indent=5)

        self.download_storepage(extid, extdir)
        self.download_extension(extid, extdir)

    def run(self, category, nrExtensions):
        sys.stdout.write('Downloading extensions into folder "{}"...\n'.format(self.basedir))
        response = requests.post(self.extension_list_url.format(nrExtensions, category)).text
        bigjson = json.loads(response.lstrip(")]}'\n"))
        extinfos = bigjson[1][1]

        newExtensions = 0
        for extinfo in extinfos:
            extid = extinfo[0]
            sys.stdout.write('Processing extension "{}"...'.format(extid))
            sys.stdout.flush()
            try:
                self.handle_extension(extinfo)
                sys.stdout.write('Done!\n')
                newExtensions += 1
            except CrawlError as cerr:
                sys.stdout.write('Error: {}\n'.format(cerr.message))
                if cerr.pagecontent != "":
                    sys.stderr.write('Page content was:\n')
                    sys.stderr.write('{}\n'.format(cerr.pagecontent))
            except UnauthorizedError as uerr:
                sys.stdout.write('Error: login needed\n')
        sys.stdout.write('Downloaded {} new extensions.\n'.format(newExtensions))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Downloads extensions from the Chrome Web Store.')
    parser.add_argument('-t', '--interval', nargs='?', const=5, type=int, help='Keep downloading extensions every X seconds.')
    parser.add_argument('-i', '--iterate', metavar='i', default=1, type=int, help='Queries the store i times for a list of extensions.')
    parser.add_argument('-n', '--nrexts', metavar='N', default=200, type=int, help='The number of extensions to be downloaded per request (Google does not accept values much higher than 200).')
    parser.add_argument('-c', '--category', default='extensions', choices=ExtensionCrawler.possible_categories, help='The extension category from which extensions should be downloaded.')
    parser.add_argument('-d', '--dest', default='downloaded', help='The directory in which the downloaded extensions should be stored.')

    args = parser.parse_args()
    crawler = ExtensionCrawler(args.dest)

    if args.interval:
        while True:
            for i in range(args.iterate):
                crawler.run(args.category, args.nrexts)
                time.sleep(args.interval)
    else:
        for i in range(args.iterate):
            crawler.run(args.category, args.nrexts)
