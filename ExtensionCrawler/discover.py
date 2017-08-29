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

"""Python mnodule providing methods for discovering extensions in the
   Chrome extension store."""

import xml.etree.ElementTree as ET
import re
from functools import reduce
import requests
import ExtensionCrawler.config
import logging


def crawl_nearly_all_of_ext_ids():
    """Crawl extension ids available in Chrome store."""
    def get_inner_elems(doc):
        """Get inner element."""
        return ET.fromstring(doc).findall(r".//{{{}}}loc".format(
            ExtensionCrawler.config.const_sitemap_scheme()))

    def is_generic_url(url):
        """Check if URL is a generic extensiosn URL."""
        return re.match(r"^{}\?shard=\d+&numshards=\d+$".format(
            ExtensionCrawler.config.const_sitemap_url()), url)

    shard_elems = get_inner_elems(
        requests.get(ExtensionCrawler.config.const_sitemap_url(), timeout=10)
        .text)
    shard_urls = list(
        # The urls with a language parameter attached return a subset
        # of the ids that get returned by the plain urls, therefore we
        # skip urls with a language parameter
        filter(is_generic_url, ([elem.text for elem in shard_elems])))
    shards = list(map(lambda u: requests.get(u, timeout=10).text, shard_urls))

    overview_urls = reduce(
        lambda x, y: x + y,
        map(lambda s: [elem.text for elem in get_inner_elems(s)], shards), [])
    return [re.search("[a-z]{32}", url).group(0) for url in overview_urls]


def get_new_ids(known_ids):
    """Discover new extension ids."""
    logging.info("Discovering new ids ...")
    discovered_ids = []
    try:
        discovered_ids = ExtensionCrawler.discover.crawl_nearly_all_of_ext_ids()
    except Exception:
        logging.exception("Exception when discovering new ids")
    new_ids = list(set(discovered_ids) - set(known_ids))
    logging.info(2 * " " + "Discovered {} new extensions (out of {})".format(
        len(new_ids), len(discovered_ids)))
    return new_ids
