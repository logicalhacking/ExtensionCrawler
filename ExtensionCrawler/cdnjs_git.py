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
import logging
import os
import re
from functools import partial, reduce
from multiprocessing import Pool
import csv
import sys

import dateutil.parser
import git

from ExtensionCrawler.file_identifiers import get_file_identifiers
from ExtensionCrawler.dbbackend.mysql_backend import MysqlBackend
import ExtensionCrawler.config as config


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
    if git_repo.is_dirty():
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
    if git_repo.is_dirty():
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
                libvers.add(reduce(os.path.join, plist[:4]))
    logging.info("Found " + str(len(files)) + " files")
    logging.info("Found " + str(len(libvers)) +
                 " unique library/version combinations.")
    return files, list(libvers)


def get_all_lib_files(cdnjs_git_path, localpath=None):
    """Return all libraries stored in cdnjs git repo."""
    libvers = set()
    files = []
    versionidx = len(path_to_list(cdnjs_git_path)) + 4
    if not localpath is None:
        paths = os.path.join(cdnjs_git_path, localpath)
    else:
        paths = os.path.join(cdnjs_git_path, 'ajax/libs/**/*')

    logging.info("Building file list for: " + str(paths))

    for fname in glob.iglob(paths, recursive=True):
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


def update_database_for_file(create_csv, release_dic, cdnjs_git_path, filename,
                             con):
    """Update database for all file."""
    if os.path.isfile(filename):
        logging.info("Updating database for file " + filename)
        file_info = get_file_libinfo(release_dic, cdnjs_git_path, filename)
        if not file_info is None:
            if create_csv:
                print(file_info['path'])
                print(cdnjs_git_path)
                file_info['path'] = re.sub(r'^.*\/ajax\/', 'ajax/',
                                           file_info['path'])
                for key in [
                        'md5', 'sha1', 'sha256', 'normalized_md5',
                        'normalized_sha1', 'normalized_sha256',
                        'dec_normalized_md5', 'dec_normalized_sha1',
                        'dec_normalized_sha256', 'dec_md5', 'dec_sha1',
                        'dec_sha256'
                ]:
                    if not file_info[key] is None:
                        file_info[key] = (file_info[key]).hex()
                csv_writer = csv.DictWriter(sys.stdout, file_info.keys())
                csv_writer.writeheader()
                csv_writer.writerow(file_info)
            else:
                logging.info("Updating database ...")
                for prefix, typ in [("", "AS_IS"), ("normalized_",
                                                    "NORMALIZED"),
                                    ("dec_", "DECOMPRESSED"),
                                    ("dec_normalized_",
                                     "DECOMPRESSED_NORMALIZED")]:
                    if file_info[prefix + "md5"] is not None:
                        con.insert(
                            "cdnjs",
                            md5=file_info[prefix + "md5"],
                            sha1=file_info[prefix + "sha1"],
                            sha256=file_info[prefix + "sha256"],
                            size=file_info[prefix + "size"],
                            loc=file_info[prefix + "loc"],
                            description=file_info[prefix + "description"],
                            encoding=file_info[prefix + "encoding"],
                            mimetype=file_info["mimetype"][0] if "mimetype" in file_info else None,
                            mimetype_detail=file_info["mimetype"][1] if "mimetype" in file_info else None,
                            path=file_info["path"],
                            filename=file_info["filename"],
                            add_date=file_info["add_date"],
                            library=file_info["library"],
                            version=file_info["version"],
                            typ=typ)

    else:
        logging.info("Skipping update for deleted file " + filename)


def update_database_for_file_chunked(create_csv, release_dic, cdnjs_git_path,
                                     filenames):
    with MysqlBackend(
            None,
            read_default_file=config.const_mysql_config_file(),
            charset='utf8mb4',
            compress=True) as con:
        for filename in filenames:
            update_database_for_file(create_csv, release_dic, cdnjs_git_path, filename,
                            con)


def chunks(l, n):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        yield l[i:i + n]


def update_database(create_csv,
                    release_dic,
                    cdnjs_git_path,
                    files,
                    poolsize=16):
    """Update database for all files in files."""
    with Pool(poolsize) as pool:
        pool.map(
            partial(update_database_for_file_chunked, create_csv, release_dic,
                    cdnjs_git_path), chunks(list(files), 200))


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


def pull_and_update_db(cdnjs_git_path, create_csv, poolsize=16):
    """Pull repo and update database."""
    files, libvers = pull_get_updated_lib_files(cdnjs_git_path)
    release_dic = build_release_date_dic(cdnjs_git_path, libvers, poolsize)
    del libvers
    gc.collect()
    update_database(create_csv, release_dic, cdnjs_git_path, files, poolsize)


def update_db_from_listfile(cdnjs_git_path, listfile, create_csv, poolsize=16):
    """Update database (without pull) for files in listfile)"""
    paths = []
    with open(listfile) as listfileobj:
        paths = listfileobj.read().splitlines()
    files = []
    libvers = []
    for path in paths:
        path_files, path_libvers = get_all_lib_files(cdnjs_git_path, path)
        libvers = libvers + path_libvers
        files = files + path_files
    logging.info("In total, found " + str(len(files)) + " files in " +
                 str(len(libvers)) + " liberies/versions.")
    release_dic = build_release_date_dic(cdnjs_git_path, libvers, poolsize)
    update_database(create_csv, release_dic, cdnjs_git_path, files, poolsize)


def update_db_all_libs(cdnjs_git_path,
                       create_csv,
                       taskid=1,
                       maxtaskid=1,
                       poolsize=16):
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
    update_database(create_csv, release_dic, cdnjs_git_path, files, poolsize)
