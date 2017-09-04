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
    at CDNJS.com."""

import datetime
import glob
import hashlib
import json
import logging
import os
import re
import sys
from functools import partial
from multiprocessing import Pool

import requests

# Script should run with python 3.4 or 3.5
assert sys.version_info >= (3, 4) and sys.version_info < (3, 6)


def get_cdnjs_all_libs_url():
    """URL for obtaining list of all available libraries, see https://cdnjs.com/api for details."""
    return "https://api.cdnjs.com/libraries"


def get_jsfile_url(lib, version, jsfile):
    """URL for obtaining detailed list of all available files/versionf of
       a JavaScript library, see https://cdnjs.com/api for details."""
    return "https://cdnjs.cloudflare.com/ajax/libs/{}/{}/{}".format(
        lib, version, jsfile)


def get_local_libs(archive):
    """Get list of locally available libraries."""
    dirname = os.path.join(archive, "fileinfo", "cdnjs", "lib")
    return (list(
        map(lambda f: re.sub(".json$", "", os.path.basename(f)),
            glob.glob(os.path.join(dirname, "*.json")))))


def update_lib(force, archive, lib):
    """Update information for a JavaScript library."""
    name = lib['name']
    try:
        lib_res = requests.get(get_cdnjs_all_libs_url() + "/" + lib['name'],
                               timeout=10)
    except Exception as e:
        logging.error("Exception during download of library overview for " +
                      name + "from " + get_cdnjs_all_libs_url() + "/" +
                      lib['name'] + ":")
        logging.error(str(e))
        return

    if not lib_res.status_code == 200:
        logging.error("  Cannot access overview for " + name +
                      "(status codce: " + str(
                          lib_res.status_code) + ") " + str(lib_res.url))
        logging.error(str(lib_res.content))
        return
    cdnjs_lib_json = lib_res.json()
    dirname = os.path.join(archive, "fileinfo", "cdnjs", "lib")
    os.makedirs(str(dirname), exist_ok=True)

    try:
        with open(os.path.join(dirname, name + ".json"), "r") as json_file:
            local_lib_json = json.load(json_file)
    except IOError:
        local_lib_json = None
    except json.decoder.JSONDecodeError:
        local_lib_json = None
        logging.warning("  JSON file (" + os.path.join(dirname, name + ".json")
                        + ") defect, re-downloading.")
        os.rename(
            os.path.join(dirname, name + ".json"),
            os.path.join(dirname, name + ".backup.json"))

    local_versions = []
    if local_lib_json is not None:
        for lib_ver in local_lib_json['assets']:
            local_versions.append(lib_ver['version'])

    cdnjs_versions = []
    for lib_ver in cdnjs_lib_json['assets']:
        cdnjs_versions.append(lib_ver['version'])

    for lib_ver in cdnjs_lib_json['assets']:
        version = lib_ver['version']
        logging.info("  Checking " + str(lib['name']) + " " + str(version))
        files_with_hashes = []
        if not force and version in local_versions:
            logging.info("    Updating from local record.")
            old_record = next(x for x in local_lib_json['assets']
                              if x['version'] == lib_ver['version'])
            files_with_hashes = old_record['files']
        else:
            logging.warning("    Updating from remote record (" + name + " " +
                            version + ").")
            for jsfile in lib_ver['files']:
                jsfile_url = get_jsfile_url(name, version, jsfile)
                logging.info("        " + jsfile_url)
                try:
                    res_jsfile = requests.get(jsfile_url, timeout=10)
                except Exception as e:
                    logging.error("Exception during download of assets of " +
                                  name + " from " + jsfile_url + ":")
                    logging.error(str(e))
                    return

                if res_jsfile.status_code == 403 or res_jsfile.status_code == 404:
                    logging.warning("Access denied: cannot access assests of " + name +
                                  " (status code: " + str(
                                      res_jsfile.status_code) + ") " + str(
                                          res_jsfile.url))
                    files_with_hashes.append({
                        'filename': jsfile,
                        'url': jsfile_url,
                        'first_seen': datetime.datetime.utcnow().isoformat(),
                        'http_status_code': res_jsfile.status_code
                    })
                elif res_jsfile.status_code == 200:
                    data = res_jsfile.content
                    files_with_hashes.append({
                        'filename': jsfile,
                        'md5': hashlib.md5(data).hexdigest(),
                        'sha1': hashlib.sha1(data).hexdigest(),
                        'sha256': hashlib.sha256(data).hexdigest(),
                        'url': jsfile_url,
                        'first_seen': datetime.datetime.utcnow().isoformat(),
                        'size': len(data),
                        'http_status_code': res_jsfile.status_code
                    })
                else:
                    logging.error("Unknown error: cannot access assests of " + name +
                                  " (status code: " + str(
                                      res_jsfile.status_code) + ") " + str(
                                          res_jsfile.url))
                    logging.error(str(res_jsfile.content))
                    return

        lib_ver['files'] = files_with_hashes

    if local_lib_json is not None:
        outphased = []
        for lib_ver in local_lib_json['assets']:
            version = lib_ver['version']
            if not version in cdnjs_versions:
                logging.warning("Found outphased versions for " + name + " " +
                                str(version) + " , preserving from archive.")
                if not 'outphased' in lib_ver:
                    lib_ver['outphased'] = datetime.datetime.utcnow(
                    ).isoformat()
                outphased.append(lib_ver)
        if outphased:
            cdnjs_lib_json['assets'] = cdnjs_lib_json['assets'] + outphased

    output = os.path.join(dirname, name + ".json")
    logging.info("    Saving " + str(output))
    with open(output, "w") as json_file:
        json.dump(cdnjs_lib_json, json_file)


def build_hash_map_of_lib(hashalg, archive, lib):
    """Build dictionary with file information using the file hash as key."""
    dirname = os.path.join(archive, "fileinfo", "cdnjs", "lib")
    hash_map = {}
    try:
        with open(os.path.join(dirname, lib + ".json"), "r") as json_file:
            local_lib_json = json.load(json_file)
    except IOError:
        return None
    for lib_ver in local_lib_json['assets']:
        version = lib_ver['version']
        for jsfile in lib_ver['files']:
            hashvalue = jsfile[hashalg]
            hash_map[hashvalue] = {
                'library': lib,
                'version': version,
                'file': jsfile['filename'],
                'first_seen': jsfile['first_seen']
            }
            if 'outphased' in jsfile:
                (hash_map[hashvalue])['outphased'] = jsfile['outphased']
    return hash_map


def build_sha1_map_of_lib(archive, lib):
    """Build dictionary with file information using the file sha1 as key."""
    return build_hash_map_of_lib("sha1", archive, lib)


def build_md5_map_of_lib(archive, lib):
    """Build dictionary with file information using the file md5 as key."""
    return build_hash_map_of_lib("md5", archive, lib)


def build_hash_map(hashalg, archive):
    """Build file information dictionary using the file hash as key"""
    hash_map = None
    for lib in get_local_libs(archive):
        lib_map = build_hash_map_of_lib(hashalg, archive, lib)
        if lib_map is not None and hash_map is not None:
            hash_map.update(lib_map)
        else:
            hash_map = lib_map
    return hash_map


def build_sha1_map(archive):
    """Build file information dictionary using the sha1 hash as key"""
    return build_hash_map("sha1", archive)


def build_md5_map(archive):
    """Build file information dictionary using the md5 hash as key"""
    return build_hash_map("md5", archive)


def update_md5_map_file(archive):
    """Update file containing md5 information for all files."""
    with open(os.path.join(archive, "fileinfo", "cdnjs-md5.json"),
              "w") as json_file:
        json.dump(build_md5_map(archive), json_file)


def update_sha1_map_file(archive):
    """Update file containing sha1 information for all files."""
    with open(os.path.join(archive, "fileinfo", "cdnjs-sha1.json"),
              "w") as json_file:
        json.dump(build_sha1_map(archive), json_file)


def delete_orphaned(archive, local_libs, cdnjs_current_libs):
    """Delete all orphaned local libaries."""
    dirname = os.path.join(archive, "fileinfo", "cdnjs", "lib")
    for lib in local_libs:
        if not lib in cdnjs_current_libs:
            os.remove(os.path.join(dirname, lib + ".json"))


def update_jslib_archive(force, clean, archive):
    """Update information for all available JavaScript libraries."""
    cdnjs_all_libs_url = get_cdnjs_all_libs_url()
    try:
        res = requests.get(cdnjs_all_libs_url, timeout=10)
    except Exception as e:
        logging.error("Exception during download of library overview from " +
                      cdnjs_all_libs_url + ":")
        logging.error(str(e))
        sys.exit(1)

    if not res.status_code == 200:
        logging.error("Could not obtain library overview (http status code: " +
                      str(res.status_code) + ")")
        logging.error(str(res.content))
        sys.exit(1)

    cdnjs_lib_catalog = res.json()['results']
    if clean:
        local_lib_catalog = get_local_libs(archive)
        delete_orphaned(archive, local_lib_catalog, cdnjs_lib_catalog)
    dirname = os.path.join(archive, "fileinfo", "cdnjs")
    os.makedirs(str(dirname), exist_ok=True)
    with open(os.path.join(dirname, "cdnjs-libraries.json"), "w") as json_file:
        json.dump(res.json(), json_file)
    logging.info("Found " + str(len(cdnjs_lib_catalog)) +
                 " different libraries")

    with Pool(32) as p:
        p.map(partial(update_lib, force, archive), cdnjs_lib_catalog)
