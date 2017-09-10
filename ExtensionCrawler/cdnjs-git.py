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

import git
import dateutil.parser


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
    for fi in fetch_info:
        for diff in fi.commit.diff(fi.old_commit):
            if not diff.a_blob.path in files:
                files.append(diff.a_blob.path)
    return files
