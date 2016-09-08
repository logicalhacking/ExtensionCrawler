import requests
import time
import sys
import os
import json
import re

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
    regexExtid       = re.compile(r'^[a-z]+$')
    regexExtfilename = re.compile(r'^extension[_0-9]+\.crx$')

    downloadUrl      = 'https://clients2.google.com/service/update2/crx?response=redirect&nacl_arch=x86-64&prodversion=9999.0.9999.0&x=id%3D{}%26uc'
    extensionListUrl = 'https://chrome.google.com/webstore/ajax/item?pv=20160822&count=200&category=extensions'
    detailUrl        = 'https://chrome.google.com/webstore/detail/{}'

    def __init__(self, basedir):
        self.basedir = basedir

    def downloadExtension(self, extid, extdir=""):
        extresult = requests.get(self.downloadUrl.format(extid), stream=True)
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

    def downloadStorepage(self, extid, extdir):
        extpageresult = requests.get(self.detailUrl.format(extid))
        with open(os.path.join(extdir, 'storepage.html'), 'w') as f:
            f.write(extpageresult.text)

    def handleExtension(self, extinfo):
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

        self.downloadStorepage(extid, extdir)
        self.downloadExtension(extid, extdir)

    def run(self, nrExtensions):
        sys.stdout.write('Downloading extensions into folder "{}"...\n'.format(self.basedir))
        bigjson = json.loads(requests.post(self.extensionListUrl.format(nrExtensions)).text.lstrip(")]}'\n"))
        extinfos = bigjson[1][1]

        newExtensions = 0
        for extinfo in extinfos:
            extid = extinfo[0]
            sys.stdout.write('Processing extension "{}"...'.format(extid))
            sys.stdout.flush()
            try:
                self.handleExtension(extinfo)
                sys.stdout.write('Done!\n')
                newExtensions += 1
            except CrawlError as cerr:
                sys.stdout.write('Error: {}\n'.format(cerr.message))
                if cerr.pagecontent != "":
                    sys.stderr.write('Page content was:\n')
                    sys.stderr.write('{}\n'.format(cerr.pagecontent))
            except UnauthorizedError as uerr:
                sys.stdout.write('Error: login needed')
        sys.stdout.write('Downloaded {} new extensions.\n'.format(newExtensions))

if __name__ == '__main__':
    crawler = ExtensionCrawler('downloaded')

    # 200 extensions is roughly the maximum number allowed
    crawler.run(200)
