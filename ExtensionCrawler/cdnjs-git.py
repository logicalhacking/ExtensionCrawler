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
""" Module for obtaining md5/sha1/sha256 hashes for all files available
    at CDNJS.com by mining the cdnjs git repository."""

import hashlib
import mimetypes
import os
from functools import reduce

import cchardet as chardet
import dateutil.parser
import git
import magic

from ExtensionCrawler.js_mincer import mince_js


def get_add_date(gitobj, filename):
    """Method for getting the initial add/commit date of a file."""
    try:
        add_date_string = gitobj.log("--follow", "--format=%aD", "--reverse",
                                     filename).splitlines()[0]
        return dateutil.parser.parse(add_date_string)
    except Exception:
        return None


def pull_get_list_changed_files(gitrepo):
    """Pull new updates from remote origin."""
    files = []
    cdnjs_origin = gitrepo.remotes.origin
    fetch_info = cdnjs_origin.pull()
    for single_fetch_info in fetch_info:
        for diff in single_fetch_info.commit.diff(
                single_fetch_info.old_commit):
            if not diff.a_blob.path in files:
                files.append(diff.a_blob.path)
    return files


def normalize_file(path, encoding):
    """Compute normalized code blocks of a JavaScript file"""
    txt = ""
    with open(path, encoding=encoding) as fileobj:
        for block in mince_js(fileobj):
            if block.is_code():
                for line in block.content.splitlines():
                    txt += line.strip()
    return txt.encode()


def get_file_identifiers(path):
    """Get basic file identifiers (size, hashes, normalized hashes, etc.)."""
    with open(path, 'rb') as fileobj:
        data = fileobj.read()

    file_identifier = {
        'filename': os.path.basename(path),
        'path': path,
        'md5': hashlib.md5(data).digest(),
        'sha1': hashlib.sha1(data).digest(),
        'sha256': hashlib.sha256(data).digest(),
        'size': len(data),
        'mimetype': mimetypes.guess_type(path),
        'description': magic.from_file(path),
        'encoding': chardet.detect(data)['encoding'],
    }

    try:
        normalized_data = normalize_file(path, file_identifier['encoding'])
    except Exception:
        normalized_data = None

    if normalized_data is None:
        file_identifier['normalized_md5'] = None
        file_identifier['normalized_sha1'] = None
        file_identifier['normalized_sha256'] = None
    else:
        normalized_data = normalize_file(path, file_identifier['encoding'])
        file_identifier['normalized_md5'] = hashlib.md5(
            normalized_data).digest()
        file_identifier['normalized_sha1'] = hashlib.sha1(
            normalized_data).digest()
        file_identifier['normalized_sha256'] = hashlib.sha256(
            normalized_data).digest()

    return file_identifier


def path_to_list(path):
    """Convert a path (string) to a list of folders/files."""
    plist = []
    while(True):
        (head,tail) = os.path.split(path)
        if head == '':
            if tail == '':
                break
            else:
                plist.append(tail)
                break
        else:
            if tail == '':
                plist.append(head)
                break
            else:
                plist.append(tail)
                path = head
    return list(reversed(plist))

def get_file_libinfo(gitobj, libfile):
    """Compute file idenfifiers and library information of libfile."""
    try:
        file_info = get_file_identifiers(libfile)
        plist = path_to_list(libfile)
        idx = plist.index("libs")
        file_info['library'] = plist[idx+1]
        file_info['version'] = plist[idx+2]
        file_info['add_date'] = get_add_date(gitobj, libfile)
        package = os.path.join(reduce(os.path.join, plist[:idx+1]), "package.json")
        return file_info
    except Exception:
        return None
