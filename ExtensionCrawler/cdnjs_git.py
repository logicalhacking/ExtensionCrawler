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

import gc
import glob
import hashlib
import logging
import mimetypes
import os
import re
import zlib
from functools import partial, reduce
from io import StringIO
from multiprocessing import Pool

import cchardet as chardet
import dateutil.parser
import git
import magic

from ExtensionCrawler.js_mincer import mince_js


def get_add_date(git_path, filename):
    """Method for getting the initial add/commit date of a file."""
    try:
        gitobj = git.Git(git_path)
        add_date_string = gitobj.log("--follow", "--format=%aD", "--reverse",
                                     filename).splitlines()[0]
        del gitobj
        gc.collect()
        return dateutil.parser.parse(add_date_string)
    except Exception as e:
        logging.debug("Exception during git log for " + filename + ":\n" +
                      (str(e)))
        return None


def pull_list_changed_files(git_path):
    """Pull new updates from remote origin."""
    git_repo = git.Repo(git_path)
    logging.info(" HEAD: " + str(git_repo.head.commit))
    logging.info("   is detached: " + str(git_repo.head.is_detached))
    logging.info("   is dirty: " + str(git_repo.is_dirty()))
    if git_repo.head.is_detached:
        raise Exception("Detached head")
    if git_repo.is_dirty:
        raise Exception("Dirty repository")

    files = []
    cdnjs_origin = git_repo.remotes.origin
    fetch_info = cdnjs_origin.pull()
    for single_fetch_info in fetch_info:
        for diff in single_fetch_info.commit.diff(
                single_fetch_info.old_commit):
            logging.debug("Found diff: " + str(diff))
            if not diff.a_blob is None:
                if not diff.a_blob.path in files:
                    files.append(diff.a_blob.path)
    return files


def hackish_pull_list_changed_files(git_path):
    """Pull new updates from remote origin (hack, using git binary - 
       faster but not as safe as GitPython)."""
    git_repo = git.Repo(git_path)
    logging.info(" HEAD: " + str(git_repo.head.commit))
    logging.info("   is detached: " + str(git_repo.head.is_detached))
    logging.info("   is dirty: " + str(git_repo.is_dirty()))
    if git_repo.head.is_detached:
        raise Exception("Detached head")
    if git_repo.is_dirty:
        raise Exception("Dirty repository")
    del git_repo
    gc.collect()

    files = set()
    git_obj = git.Git(git_path)

    for line in git_obj.pull().splitlines():
        match = re.search(r'^ (.+) \| .*$', line)
        if not match is None:
            changed_files = match.group(1).split('=>')
            for changed_file in changed_files:
                files.add(changed_file.strip())
    return list(files)


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


def get_file_libinfo(release_dic, git_path, libfile):
    """Compute file idenfifiers and library information of libfile."""
    logging.info("Computing file info for " + libfile)
    try:
        file_info = get_file_identifiers(libfile)
        plist = path_to_list(libfile)
        idx = plist.index("libs")
        lib = plist[idx + 1]
        version = plist[idx + 2]
        file_info['library'] = lib
        file_info['version'] = version
        file_info['add_date'] = release_dic[(lib, version)]
        package = os.path.join(
            reduce(os.path.join, plist[:idx + 1]), "package.json")
        return file_info
    except Exception:
        return None


def pull_get_updated_lib_files(cdnjs_git_path):
    """Pull repository and determine updated libraries."""
    logging.info("Building file list (only updates)")
    libvers = set()
    files = []
    for update in hackish_pull_list_changed_files(cdnjs_git_path):
        if not (os.path.basename(update) in ["package.json", ".gitkeep"]):
            if update.startswith("ajax"):
                fname = os.path.join(cdnjs_git_path, update)
                files.append(fname)
                plist = path_to_list(update)
                if len(plist) == 4:
                    libvers.add(fname)
    logging.info("Found " + str(len(files)) + " files")
    logging.info("Found " + str(len(libvers)) +
                 " unique library/version combinations.")
    return files, list(libvers)


def get_all_lib_files(cdnjs_git_path):
    """Return all libraries stored in cdnjs git repo."""
    logging.info("Building file list (complete repository)")
    libvers = set()
    files = []
    versionidx = len(path_to_list(cdnjs_git_path)) + 4
    for fname in glob.iglob(
            os.path.join(cdnjs_git_path, 'ajax/libs/**/*'), recursive=True):
        if not os.path.isdir(fname):
            if not os.path.basename(fname) in ["package.json", ".gitkeep"]:
                files.append(fname)
        else:
            plist = path_to_list(fname)
            if len(plist) == versionidx:
                libvers.add(fname)
    gc.collect()

    logging.info("Found " + str(len(files)) + " files")
    logging.info("Found " + str(len(libvers)) +
                 " unique library/version combinations.")
    return files, list(libvers)


def update_database_for_file(release_dic, cdnjs_git_path, filename):
    """Update database for all file."""
    if os.path.isfile(filename):
        logging.info("Updating database for file " + filename)
        file_info = get_file_libinfo(release_dic, cdnjs_git_path, filename)
        if not file_info is None:
            ## TODO
            logging.info("Updating database ...")
    else:
        logging.info("Skipping update for deleted file " + filename)

def update_database(release_dic, cdnjs_git_path, files, poolsize=16):
    """Update database for all files in files."""
    with Pool(poolsize) as pool:
        pool.map(
            partial(update_database_for_file, release_dic, cdnjs_git_path),
            files)


def get_release_triple(git_path, libver):
    plist = path_to_list(libver)
    ver = plist[-1]
    lib = plist[-2]
    date = get_add_date(git_path, libver)
    logging.info(lib + " " + ver + ": " + str(date))
    return (lib, ver, date)


def build_release_date_dic(git_path, libvers, poolsize=16):
    """"Build dictionary of release date with the tuple (library, version) as key."""
    logging.info("Building release dictionary")
    with Pool(poolsize) as pool:
        libverdates = pool.map(partial(get_release_triple, git_path), libvers)
    release_date_dic = {}
    for (lib, ver, date) in libverdates:
        release_date_dic[(lib, ver)] = date
    return release_date_dic


def pull_and_update_db(cdnjs_git_path, poolsize=16):
    """Pull repo and update database."""
    files, libvers = pull_get_updated_lib_files(cdnjs_git_path)
    release_dic = build_release_date_dic(cdnjs_git_path, libvers, poolsize)
    del libvers
    gc.collect()
    update_database(release_dic, cdnjs_git_path, files, poolsize)


def update_db_all_libs(cdnjs_git_path, taskid=1, maxtaskid=1, poolsize=16):
    """Update database entries for all libs in git repo."""
    files, libvers = get_all_lib_files(cdnjs_git_path)

    if maxtaskid > 1:
        logging.info("Running task " + str(taskid) + " of " + str(maxtaskid))
        chunksize = int(len(files) / maxtaskid)
        if taskid == maxtaskid:
            files = files[(taskid - 1) * chunksize:]
        else:
            files = files[(taskid - 1) * chunksize:taskid * chunksize]
        libvers = set()
        versionidx = len(path_to_list(cdnjs_git_path)) + 4
        for path in files:
            libvers.add(path[:versionidx + 5])
        libvers = list(libvers)
        logging.info("This task has  " + str(len(files)) + " files from  " +
                     str(len(libvers)) + " library version(s).")

    release_dic = build_release_date_dic(cdnjs_git_path, libvers, poolsize)
    del libvers
    gc.collect()
    update_database(release_dic, cdnjs_git_path, files, poolsize)
