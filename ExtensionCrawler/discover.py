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
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""Python mnodule providing methods for discovering extensions in the
   Chrome extension store."""

from xml.etree.ElementTree import fromstring
import re
import requests
from pebble import ThreadPool
from ExtensionCrawler import config


def get_inner_elems(doc):
    """Get inner element."""
    return fromstring(doc).iterfind(r".//{{{}}}loc".format(
        config.const_sitemap_scheme()))


def is_generic_url(url):
    """Check if URL is a generic extension URL."""
    """The urls with a language parameter attached return a subset"""
    """of the ids that get returned by the plain urls, therefore we"""
    """skip urls with a language parameter."""

    return re.match(r"^{}\?shard=\d+&numshards=\d+$".format(
        config.const_sitemap_url()), url)


def iterate_shard(shard_url):
    if is_generic_url(shard_url):
        shard = requests.get(shard_url, timeout=10).text
        for inner_elem in get_inner_elems(shard):
            overview_url = inner_elem.text
            yield re.search("[a-z]{32}", overview_url).group(0)


def process_shard(shard_url):
    return list(iterate_shard(shard_url))


def crawl_nearly_all_of_ext_ids(max_ids=None):
    """Crawl extension ids available in Chrome store."""

    shard_urls = [shard_elem.text for shard_elem in get_inner_elems(
            requests.get(config.const_sitemap_url(), timeout=10).text)]
    with ThreadPool(16) as pool:
        future = pool.map(process_shard, shard_urls, chunksize=1)
        iterator = future.result()

        returned_ids = 0
        while True:
            try:
                for extid in next(iterator):
                    yield extid
                    returned_ids += 1
                    if max_ids is not None and returned_ids >= max_ids:
                        pool.stop()
                        return
            except StopIteration:
                return

def get_new_ids(known_ids, max_ids=None):
    """Discover new extension ids."""
    for discovered_id in crawl_nearly_all_of_ext_ids(max_ids):
        if discovered_id not in known_ids:
            yield discovered_id
