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
import hashlib
import json
import os
import glob
import re
import sys

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
    return (list(map(lambda f: re.sub(".json$", "", os.path.basename(f),
                                      glob.glob(os.path.join(dirname, "*.json"))))))

def update_lib(verbose, force, archive, lib):
    """Update information for a JavaScript library."""
    name = lib['name']
    lib_res = requests.get(get_cdnjs_all_libs_url() + "/" + lib['name'])
    cdnjs_lib_json = lib_res.json()
    dirname = os.path.join(archive, "fileinfo", "cdnjs", "lib")
    os.makedirs(str(dirname), exist_ok=True)

    try:
        with open(os.path.join(dirname, name + ".json"), "r") as json_file:
            local_lib_json = json.load(json_file)
    except IOError:
        local_lib_json = None

    local_versions = []
    if local_lib_json is not None:
        for lib_ver in local_lib_json['assets']:
            local_versions.append(lib_ver['version'])

    for lib_ver in cdnjs_lib_json['assets']:
        version = lib_ver['version']
        if verbose:
            print("Checking", lib['name'], version)
        files_with_hashes = []
        if not force and version in local_versions:
            print("    Updating from local record.")
            old_record = next(x for x in local_lib_json['assets'] if x['version'] == lib_ver['version'])
            files_with_hashes = old_record['files']
        else:
            print("    Updating from remote record.")
            for jsfile in lib_ver['files']:
                jsfile_url = get_jsfile_url(name, version, jsfile)
                if verbose:
                    print("        "+jsfile_url)
                res_jsfile = requests.get(jsfile_url)
                data = res_jsfile.content
                files_with_hashes.append({
                    'filename': jsfile,
                    'md5': hashlib.md5(data).hexdigest(),
                    'sha1': hashlib.sha1(data).hexdigest(),
                    'sha256': hashlib.sha256(data).hexdigest(),
                    'url': jsfile_url,
                    'date': datetime.datetime.utcnow().isoformat(),
                    'size': len(data)
                })

        lib_ver['files'] = files_with_hashes
        with open(os.path.join(dirname, name + ".json"), "w") as json_file:
            json.dump(cdnjs_lib_json, json_file)

def delete_orphaned(archive, local_libs, cdnjs_current_libs):
    """Delete all orphaned local libaries."""
    dirname = os.path.join(archive, "fileinfo", "cdnjs", "lib")
    for lib in local_libs:
        if not lib in cdnjs_current_libs:
            os.remove(os.path.join(dirname, lib + ".json"))


def update_jslib_archive(verbose, force, clean, archive):
    """Update information for all available JavaScript libraries."""
    cdnjs_all_libs_url = get_cdnjs_all_libs_url()
    res = requests.get(cdnjs_all_libs_url)
    cdnjs_lib_catalog = res.json()['results']
    if clean:
        local_lib_catalog = get_local_libs(archive)
        delete_orphaned(archive, local_lib_catalog, cdnjs_lib_catalog)
    dirname = os.path.join(archive, "fileinfo", "cdnjs")
    os.makedirs(str(dirname), exist_ok=True)
    with open(os.path.join(dirname, "cdnjs-libraries.json"), "w") as json_file:
        json.dump(res.json(), json_file)
    for lib in cdnjs_lib_catalog:
        update_lib(verbose, force, archive, lib)
