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

import os
import json


def const_sitemap_url():
    return "https://chrome.google.com/webstore/sitemap"


def const_sitemap_scheme():
    return "http://www.sitemaps.org/schemas/sitemap/0.9"


def const_overview_url(id):
    return 'https://chrome.google.com/webstore/detail/{}'.format(id)


def const_store_url():
    return 'https://chrome.google.com/webstore'


def const_review_url():
    return 'https://chrome.google.com/reviews/components'


def const_review_search_url():
    return 'https://chrome.google.com/reviews/json/search'


def const_support_url():
    return 'https://chrome.google.com/reviews/components'


def const_download_url():
    return 'https://clients2.google.com/service/update2/crx?response=redirect&nacl_arch=x86-64&prodversion=9999.0.9999.0&x=id%3D{}%26uc'


def const_categories():
    return [
        'extensions', 'ext/22-accessibility', 'ext/10-blogging',
        'ext/15-by-google', 'ext/11-web-development', 'ext/14-fun',
        'ext/6-news', 'ext/28-photos', 'ext/7-productivity',
        'ext/38-search-tools', 'ext/12-shopping', 'ext/1-communication',
        'ext/13-sports'
    ]


def const_support_payload(ext_id, start, end):
    return (
        'req={{ "appId":94,' + '"version":"150922",' + '"hl":"en",' +
        '"specs":[{{"type":"CommentThread",' +
        '"url":"http%3A%2F%2Fchrome.google.com%2Fextensions%2Fpermalink%3Fid%3D{}",'
        + '"groups":"chrome_webstore_support",' + '"startindex":"{}",' +
        '"numresults":"{}",' + '"id":"379"}}],' + '"internedKeys":[],' +
        '"internedValues":[]}}').format(ext_id, start, end)


def const_review_payload(ext_id, start, end):
    return (
        'req={{ "appId":94,' + '"version":"150922",' + '"hl":"en",' +
        '"specs":[{{"type":"CommentThread",' +
        '"url":"http%3A%2F%2Fchrome.google.com%2Fextensions%2Fpermalink%3Fid%3D{}",'
        + '"groups":"chrome_webstore",' + '"sortby":"cws_qscore",' +
        '"startindex":"{}",' + '"numresults":"{}",' + '"id":"428"}}],' +
        '"internedKeys":[],' + '"internedValues":[]}}').format(
            ext_id, start, end)


def const_review_search_payload(params):
    pre = """req={"applicationId":94,"searchSpecs":["""
    post = """]}&requestSource=widget"""
    args = []
    for extid, author, start, numresults, groups in params:
        args += [
            """{{"requireComment":true,"entities":[{{"annotation":"""
            """{{"groups":{},"author":"{}","""
            """"url":"http://chrome.google.com/extensions/permalink?id={}"}}}}],"""
            """"matchExtraGroups":true,"startIndex":{},"numResults":{},"""
            """"includeNicknames":true,"locale": {{"language": "en","country": "us"}}}}"""
            .format(json.dumps(groups), author, extid, start, numresults)
        ]

    return pre + ",".join(args) + post


def get_local_archive_dir(id):
    return "{}".format(id[:3])


def archive_file(archivedir, ext_id):
    return os.path.join(
        str(archivedir), get_local_archive_dir(ext_id), ext_id + ".tar")


def db_file(archivedir, ext_id):
    return os.path.join(archivedir,
                        get_local_archive_dir(ext_id), ext_id + ".sqlite")

def jsloc_timeout():
    # Maximum number of seconds for counting jsloc per extension
    return 600
