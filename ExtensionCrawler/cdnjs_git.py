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
import logging
import mimetypes
import os
import glob
import zlib
from functools import reduce
from io import StringIO

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


def normalize_jsdata(str_data):
    """Compute normalized code blocks of a JavaScript file"""
    txt = ""
    with StringIO(str_data) as str_obj:
        for block in mince_js(str_obj):
            if block.is_code():
                for line in block.content.splitlines():
                    txt += line.strip()
    return txt.encode()


def get_data_identifiers(data):
    """Get basic data identifiers (size, hashes, normalized hashes, etc.)."""
    data_identifier = {
        'md5': hashlib.md5(data).digest(),
        'sha1': hashlib.sha1(data).digest(),
        'sha256': hashlib.sha256(data).digest(),
        'size': len(data),
        'description': magic.from_buffer(data),
        'encoding': chardet.detect(data)['encoding'],
    }
    try:
        normalized_data = normalize_jsdata(
            data.decode(data_identifier['encoding']))
    except Exception:
        normalized_data = None

    if normalized_data is None:
        data_identifier['normalized_md5'] = None
        data_identifier['normalized_sha1'] = None
        data_identifier['normalized_sha256'] = None
    else:
        data_identifier['normalized_md5'] = hashlib.md5(
            normalized_data).digest()
        data_identifier['normalized_sha1'] = hashlib.sha1(
            normalized_data).digest()
        data_identifier['normalized_sha256'] = hashlib.sha256(
            normalized_data).digest()
    return data_identifier


def get_file_identifiers(path):
    """Get basic file identifiers (path, filename, etc.) and data identifiers."""
    with open(path, 'rb') as fileobj:
        data = fileobj.read()

    data_identifier = get_data_identifiers(data)

    dec_data_identifier = {
        'md5': None,
        'sha1': None,
        'sha256': None,
        'size': None,
        'description': None,
        'encoding': None,
        'normalized_md5': None,
        'normalized_sha1': None,
        'normalized_sha256': None
    }
    if data_identifier['description'].startswith('gzip'):
        try:
            with zlib.decompressobj(zlib.MAX_WBITS | 16) as dec:
                dec_data = dec.decompress(data, 100 * data_identifier['size'])
            dec_data_identifier = get_data_identifiers(dec_data)
        except Exception as e:
            dec_data_identifier[
                'description'] = "Exception during compression (likely zip-bomb:" + str(
                    e)

    data = None
    dec_data = None

    file_identifier = {
        'filename': os.path.basename(path),
        'path': path,
        'mimetype': mimetypes.guess_type(path),
        'md5': data_identifier['md5'],
        'sha1': data_identifier['sha1'],
        'sha256': data_identifier['sha256'],
        'size': data_identifier['size'],
        'description': data_identifier['description'],
        'encoding': data_identifier['encoding'],
        'normalized_md5': data_identifier['normalized_md5'],
        'normalized_sha1': data_identifier['normalized_sha1'],
        'normalized_sha256': data_identifier['normalized_sha256'],
        'dec_md5': dec_data_identifier['md5'],
        'dec_sha1': dec_data_identifier['sha1'],
        'dec_sha256': dec_data_identifier['sha256'],
        'dec_size': dec_data_identifier['size'],
        'dec_description': dec_data_identifier['description'],
        'dec_encoding': dec_data_identifier['encoding'],
        'dec_normalized_md5': dec_data_identifier['normalized_md5'],
        'dec_normalized_sha1': dec_data_identifier['normalized_sha1'],
        'dec_normalized_sha256': dec_data_identifier['normalized_sha256']
    }

    return file_identifier


def path_to_list(path):
    """Convert a path (string) to a list of folders/files."""
    plist = []
    while True:
        (head, tail) = os.path.split(path)
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
    logging.info("Computing file info for " + libfile)
    try:
        file_info = get_file_identifiers(libfile)
        plist = path_to_list(libfile)
        idx = plist.index("libs")
        file_info['library'] = plist[idx + 1]
        file_info['version'] = plist[idx + 2]
        file_info['add_date'] = get_add_date(gitobj, libfile)
        package = os.path.join(
            reduce(os.path.join, plist[:idx + 1]), "package.json")
        return file_info
    except Exception:
        return None


def pull_get_updated_lib_files(cdnjs_repo):
    """Pull repository and determine updated libraries."""
    logging.info("Building file list (only updates)")
    files = []
    for update in pull_get_list_changed_files(cdnjs_repo):
        if not (os.path.basename(update) in ["package.json", ".gitkeep"]):
            if update.startswith("ajax"):
                files.append(update)
    logging.info("Found " + str(len(files)) + " files")
    return files


def get_all_lib_files(cdnjs_git_path):
    """Return all libraries stored in cdnjs git repo."""
    logging.info("Building file list (complete repository)")
    files = []
    for fname in glob.iglob(
            os.path.join(cdnjs_git_path, 'ajax/libs/**/*'), recursive=True):
        if not os.path.basename(fname) in ["package.json", ".gitkeep"]:
            if not os.path.isdir(fname):
                files.append(fname)
    logging.info("Found " + str(len(files)) + " files")
    return files


def update_database(cdnjs_git, files):
    """Update database for all files in files."""
    # could be converted to parallel map
    for fname in files:
        file_info = get_file_libinfo(cdnjs_git, fname)
        if not file_info is None:
            ## TODO
            logging.info("Updating database")


def pull_and_update_db(cdnjs_git_path):
    """Pull repo and update database."""
    cdnjs_git = git.Git(cdnjs_git_path)
    cdnjs_repo = git.Repo(cdnjs_git_path)
    files = pull_get_updated_lib_files(cdnjs_repo)
    update_database(cdnjs_git, files)


def update_db_all_libs(cdnjs_git_path):
    """Update database entries for all libs in git repo."""
    cdnjs_git = git.Git(cdnjs_git_path)
    files = get_all_lib_files(cdnjs_git_path)
    update_database(cdnjs_git, files)
