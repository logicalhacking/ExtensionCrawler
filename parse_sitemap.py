#!/bin/env python3

import sys
import xml.etree.ElementTree as ET
import requests
import re

ids = []

sitemap = requests.get('https://chrome.google.com/webstore/sitemap').text
shard_urls = [elem.text for elem in ET.fromstring(sitemap).findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
for shard_url in shard_urls:
    if not re.match("^https://chrome.google.com/webstore/sitemap\?shard=\d+&numshards=\d+$", shard_url):
        # The urls with a language parameter attached return a subset of the ids
        # that get returned by the plain urls, therefore we skip urls with a
        # language parameter
        continue
    shard = requests.get(shard_url).text
    detail_urls = [elem.text for elem in ET.fromstring(shard).findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
    new_ids = [re.search("[a-z]{32}", url).group(0) for url in detail_urls]
    ids = sorted(set(new_ids + ids))

for idd in ids:
    print(idd)

