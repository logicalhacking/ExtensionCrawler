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
#
""" Module for obtaining (normalized) hashes for files."""

import hashlib
import os
import re
import zlib
import mimetypes
from io import StringIO
from simhash import Simhash

import cchardet as chardet
import magic

from ExtensionCrawler.js_mincer import mince_js


def is_binary_resource(mimetype_magic):
    return (mimetype_magic.startswith("image/") or
            mimetype_magic.startswith("video/") or
            mimetype_magic.startswith("audio/") or
            mimetype_magic == "application/pdf")


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


def get_features(s):
    """Compute feature set of text (represented as string)."""
    width = 3
    s = s.lower()
    s = re.sub(r'[^\w]+', '', s)
    return [s[i:i + width] for i in range(max(len(s) - width + 1, 1))]


def get_simhash(encoding, data):
    """Compute simhash of text."""
    if encoding is not None:
        str_data = data.decode(encoding=encoding, errors="replace")
    else:
        str_data = str(data)
    simhash = Simhash(get_features(str_data)).value
    return simhash


def compute_difference(hx, hy):
    """Compute difference between two simhashes."""
    assert hx.bit_length() == hy.bit_length()
    h = (hx ^ hy) & ((1 << 64) - 1)
    d = 0
    while h:
        d += 1
        h &= h - 1
    return d


def get_data_identifiers(data):
    """Get basic data identifiers (size, hashes, normalized hashes, etc.)."""

    data_identifier = {
        'encoding': None,
        'description': None,
        'size': None,
        'loc': None,
        'mimetype_magic': None,
        'md5': None,
        'sha1': None,
        'sha256': None,
        'simhash': None,
        'size_stripped': None,
        'normalized_encoding': None,
        'normalized_description': None,
        'normalized_size': None,
        'normalized_loc': None,
        'normalized_mimetype_magic': None,
        'normalized_md5': None,
        'normalized_sha1': None,
        'normalized_sha256': None,
        'normalized_simhash': None
    }

    mimetype_magic = magic.from_buffer(data, mime=True)

    try:
        magic_desc = magic.from_buffer(data)
    except magic.MagicException as exp:
        rgx = re.compile(r' name use count.*$')
        msg = str(exp.message)
        if re.search(rgx, msg):
            magic_desc = re.sub(rgx, '', msg)
        else:
            raise exp

    data_identifier['mimetype_magic'] = mimetype_magic
    data_identifier['md5'] = hashlib.md5(data).digest()
    data_identifier['sha1'] = hashlib.sha1(data).digest()
    data_identifier['sha256'] = hashlib.sha256(data).digest()
    data_identifier['size'] = len(data)
    data_identifier['description'] = magic_desc

    # We don't continue here with binary files, as that consumes too many
    # resources.
    if is_binary_resource(mimetype_magic):
        return data_identifier

    encoding = chardet.detect(data)['encoding']

    data_identifier['simhash'] = get_simhash(encoding, data)
    data_identifier['size_stripped'] = len(data.strip())
    data_identifier['loc'] = len(data.splitlines())
    data_identifier['encoding'] = encoding
    try:
        normalized_data, normalized_loc = normalize_jsdata(
            data.decode(encoding=data_identifier['encoding'], errors="replace"))
    except Exception:
        normalized_data = None
        normalized_loc = 0

    if normalized_data is not None:
        normalized_magic_desc = ""
        try:
            normalized_magic_desc = magic.from_buffer(normalized_data)
        except magic.MagicException as exp:
            rgx = re.compile(r' name use count.*$')
            msg = str(exp.message)
            if re.search(rgx, msg):
                normalized_magic_desc = re.sub(rgx, '', msg)
            else:
                raise exp
        normalized_encoding = chardet.detect(normalized_data)['encoding']
        data_identifier['normalized_encoding'] = normalized_encoding
        data_identifier['normalized_description'] = normalized_magic_desc
        data_identifier['normalized_size'] = len(normalized_data)
        data_identifier['normalized_loc'] = normalized_loc
        data_identifier['normalized_mimetype_magic'] = magic.from_buffer(normalized_data, mime=True)
        data_identifier['normalized_md5'] = hashlib.md5(
            normalized_data).digest()
        data_identifier['normalized_sha1'] = hashlib.sha1(
            normalized_data).digest()
        data_identifier['normalized_sha256'] = hashlib.sha256(
            normalized_data).digest()
        data_identifier['normalized_simhash'] = get_simhash(
            normalized_encoding, normalized_data)
    return data_identifier


def get_file_identifiers(path, data=None):
    """Get basic file identifiers (path, filename, etc.) and data identifiers."""
    dec_data_identifier = {
        'mimetype_magic': None,
        'md5': None,
        'sha1': None,
        'sha256': None,
        'simhash': None,
        'size': None,
        'size_stripped': None,
        'loc': None,
        'description': None,
        'encoding': None,
        'normalized_mimetype_magic': None,
        'normalized_loc': None,
        'normalized_encoding': None,
        'normalized_description': None,
        'normalized_size': None,
        'normalized_md5': None,
        'normalized_sha1': None,
        'normalized_sha256': None,
        'normalized_simhash': None
    }
    if data is None:
        with open(path, 'rb') as fileobj:
            data = fileobj.read()

    data_identifier = get_data_identifiers(data)
    if data_identifier['description'].startswith('gzip'):
        try:
            dec = zlib.decompressobj(zlib.MAX_WBITS | 16)
            dec_data = dec.decompress(data, 100 * data_identifier['size'])
            dec_data_identifier = get_data_identifiers(dec_data)
            del dec_data
        except Exception as e:
            dec_data_identifier[
                'description'] = "Exception during compression (likely zip-bomb:" + str(
                    e)
    file_identifier = {
        'filename':
        os.path.basename(path),
        'path':
        path,
        'mimetype':
        mimetypes.guess_type(path),
        'mimetype_magic':
        data_identifier['mimetype_magic'],
        'md5':
        data_identifier['md5'],
        'sha1':
        data_identifier['sha1'],
        'sha256':
        data_identifier['sha256'],
        'simhash':
        data_identifier['simhash'],
        'size':
        data_identifier['size'],
        'size_stripped':
        data_identifier['size_stripped'],
        'loc':
        data_identifier['loc'],
        'description':
        data_identifier['description'],
        'encoding':
        data_identifier['encoding'],
        'normalized_encoding':
        data_identifier['normalized_encoding'],
        'normalized_description':
        data_identifier['normalized_description'],
        'normalized_size':
        data_identifier['normalized_size'],
        'normalized_loc':
        data_identifier['normalized_loc'],
        'normalized_mimetype_magic':
        data_identifier['normalized_mimetype_magic'],
        'normalized_md5':
        data_identifier['normalized_md5'],
        'normalized_sha1':
        data_identifier['normalized_sha1'],
        'normalized_sha256':
        data_identifier['normalized_sha256'],
        'normalized_simhash':
        data_identifier['normalized_simhash'],
        'dec_mimetype_magic':
        dec_data_identifier['mimetype_magic'],
        'dec_md5':
        dec_data_identifier['md5'],
        'dec_sha1':
        dec_data_identifier['sha1'],
        'dec_sha256':
        dec_data_identifier['sha256'],
        'dec_simhash':
        dec_data_identifier['simhash'],
        'dec_size':
        dec_data_identifier['size'],
        'dec_size_stripped':
        dec_data_identifier['size_stripped'],
        'dec_loc':
        dec_data_identifier['loc'],
        'dec_description':
        dec_data_identifier['description'],
        'dec_encoding':
        dec_data_identifier['encoding'],
        'dec_normalized_encoding':
        dec_data_identifier['normalized_encoding'],
        'dec_normalized_description':
        dec_data_identifier['normalized_description'],
        'dec_normalized_size':
        dec_data_identifier['normalized_size'],
        'dec_normalized_loc':
        dec_data_identifier['normalized_loc'],
        'dec_normalized_mimetype_magic':
        dec_data_identifier['normalized_mimetype_magic'],
        'dec_normalized_md5':
        dec_data_identifier['normalized_md5'],
        'dec_normalized_sha1':
        dec_data_identifier['normalized_sha1'],
        'dec_normalized_sha256':
        dec_data_identifier['normalized_sha256'],
        'dec_normalized_simhash':
        dec_data_identifier['normalized_simhash']
    }

    return file_identifier
