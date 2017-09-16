#!/usr/bin/env python3.5
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
""" Module for obtaining (normalized) md5/sha1/sha256 hashes for files."""

import gc
import hashlib
import mimetypes
import os
import zlib
from io import StringIO

import cchardet as chardet
import magic

from ExtensionCrawler.js_mincer import mince_js

def normalize_jsdata(str_data):
    """Compute normalized code blocks of a JavaScript file"""
    txt = ""
    loc = 0
    with StringIO(str_data) as str_obj:
        for block in mince_js(str_obj):
            if block.is_code():
                for line in block.content.splitlines():
                    txt += line.strip()
                    loc += 1
    return txt.encode(), loc


def get_data_identifiers(data):
    """Get basic data identifiers (size, hashes, normalized hashes, etc.)."""
    data_identifier = {
        'md5': hashlib.md5(data).digest(),
        'sha1': hashlib.sha1(data).digest(),
        'sha256': hashlib.sha256(data).digest(),
        'size': len(data),
        'loc': len(data.splitlines()),
        'description': magic.from_buffer(data),
        'encoding': chardet.detect(data)['encoding'],
    }
    try:
        normalized_data, normalized_loc = normalize_jsdata(
            data.decode(data_identifier['encoding']))
    except Exception:
        normalized_data = None

    if normalized_data is None:
        data_identifier['normalized_loc'] = None
        data_identifier['normalized_md5'] = None
        data_identifier['normalized_sha1'] = None
        data_identifier['normalized_sha256'] = None
    else:
        data_identifier['normalized_loc'] = normalized_loc
        data_identifier['normalized_md5'] = hashlib.md5(
            normalized_data).digest()
        data_identifier['normalized_sha1'] = hashlib.sha1(
            normalized_data).digest()
        data_identifier['normalized_sha256'] = hashlib.sha256(
            normalized_data).digest()
    return data_identifier


def get_file_identifiers(path):
    """Get basic file identifiers (path, filename, etc.) and data identifiers."""
    dec_data_identifier = {
        'md5': None,
        'sha1': None,
        'sha256': None,
        'size': None,
        'loc': None,
        'description': None,
        'encoding': None,
        'normalized_loc': None,
        'normalized_md5': None,
        'normalized_sha1': None,
        'normalized_sha256': None
    }
    with open(path, 'rb') as fileobj:
        data = fileobj.read()

    data_identifier = get_data_identifiers(data)

    if data_identifier['description'].startswith('gzip'):
        try:
            with zlib.decompressobj(zlib.MAX_WBITS | 16) as dec:
                dec_data = dec.decompress(data, 100 * data_identifier['size'])
                del data
            dec_data_identifier = get_data_identifiers(dec_data)
            del dec_data
        except Exception as e:
            dec_data_identifier[
                'description'] = "Exception during compression (likely zip-bomb:" + str(
                    e)
    else:
        del data
    gc.collect()
    file_identifier = {
        'filename': os.path.basename(path),
        'path': path,
        'mimetype': mimetypes.guess_type(path),
        'md5': data_identifier['md5'],
        'sha1': data_identifier['sha1'],
        'sha256': data_identifier['sha256'],
        'size': data_identifier['size'],
        'loc': data_identifier['loc'],
        'description': data_identifier['description'],
        'encoding': data_identifier['encoding'],
        'normalized_loc': data_identifier['normalized_loc'],
        'normalized_md5': data_identifier['normalized_md5'],
        'normalized_sha1': data_identifier['normalized_sha1'],
        'normalized_sha256': data_identifier['normalized_sha256'],
        'dec_md5': dec_data_identifier['md5'],
        'dec_sha1': dec_data_identifier['sha1'],
        'dec_sha256': dec_data_identifier['sha256'],
        'dec_size': dec_data_identifier['size'],
        'dec_loc': dec_data_identifier['loc'],
        'dec_description': dec_data_identifier['description'],
        'dec_encoding': dec_data_identifier['encoding'],
        'dec_normalized_loc': dec_data_identifier['normalized_loc'],
        'dec_normalized_md5': dec_data_identifier['normalized_md5'],
        'dec_normalized_sha1': dec_data_identifier['normalized_sha1'],
        'dec_normalized_sha256': dec_data_identifier['normalized_sha256']
    }

    return file_identifier
