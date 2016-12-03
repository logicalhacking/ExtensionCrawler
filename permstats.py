#!/usr/bin/env python3
#
# Copyright (C) 2016 The University of Sheffield, UK
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

from zipfile import ZipFile
import argparse
import json
import sys
import os
from jsmin import jsmin
import re

regex_concrete_url = re.compile(r'^.*://.*[a-z0-9]+\.[a-z]+.*$')


class PermissionHandlerPrintNames:
    def __init__(self, permname):
        self.permname = permname
        self.extinfo = {}

    def handle_permission(self, extid, permobj, path):
        if self.permname in str(permobj):
            with open(os.path.join(path, 'metadata.json')) as f:
                metadata = json.load(f)
                self.extinfo[extid] = '{} | {} | {}'.format(metadata[1],
                                                            metadata[6], path)

    def print_result(self, fileobj, delim):
        fileobj.write('Extensions that use permission "{}":\n\n'.format(
            self.permname))
        for extid in self.extinfo:
            fileobj.write('{}\n'.format(self.extinfo[extid]))
        fileobj.write('\n\n')


class PermissionHandler:
    def __init__(self):
        self.permissions = {}
        self.extids = set()

    def handle_permission(self, extid, permobj, path):
        self.extids.add(extid)
        perm = str(permobj)
        if not perm in self.permissions:
            self.permissions[perm] = 0
        self.permissions[perm] += 1

    def print_result(self, fileobj, delim):
        fileobj.write('Total: {} extensions\n'.format(len(self.extids)))
        for perm in sorted(
                self.permissions, key=self.permissions.get, reverse=True):
            fileobj.write('{}{}{}{}{:.2%}\n'.format(
                perm, delim, self.permissions[perm], delim,
                float(self.permissions[perm]) / len(self.extids)))
        fileobj.write('\n\n')


class PermissionHandlerCondensed:
    def __init__(self):
        self.permissions = {}
        self.extids = set()
        self.exts_with_concrete_urls = set()

    def handle_permission(self, extid, permobj, path):
        self.extids.add(extid)

        perm = str(permobj)
        if regex_concrete_url.match(perm):
            if extid in self.exts_with_concrete_urls:
                return
            self.exts_with_concrete_urls.add(extid)
            perm = '<<<{}>>>'.format(regex_concrete_url.pattern)
        if not perm in self.permissions:
            self.permissions[perm] = 0
        self.permissions[perm] += 1

    def print_result(self, fileobj, delim):
        fileobj.write('Condensed. Total: {} extensions\n'.format(
            len(self.extids)))
        for perm in sorted(
                self.permissions, key=self.permissions.get, reverse=True):
            fileobj.write('{}{}{}{}{:.2%}\n'.format(
                perm, delim, self.permissions[perm], delim,
                float(self.permissions[perm]) / len(self.extids)))
        fileobj.write('\n\n')


class PermissionStatisticGenerator:
    def run(category_folder, permhandlers):
        for root, dirs, files in os.walk(category_folder):
            crxfile = next((f for f in files if f.endswith('.crx')), None)
            if crxfile:
                extid = os.path.basename(root)
                with ZipFile(os.path.join(root, crxfile)) as zipfile:
                    with zipfile.open('manifest.json') as f:
                        content = jsmin(f.read().decode())

                        # This is needed to strip weird BOMs ...
                        first_bracket = content.find('{')
                        if first_bracket >= 0:
                            content = content[first_bracket:]

                        manifest = json.loads(content)
                        if 'permissions' in manifest:
                            for permobj in manifest['permissions']:
                                for handler in permhandlers:
                                    handler.handle_permission(extid, permobj,
                                                              root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Prints statistics about the requested permissions of downloaded extensions.'
    )
    parser.add_argument(
        'dir',
        help='The directory in which the extensions are stored. The directory structure must be {category}/{extid}/*.crx.'
    )
    parser.add_argument(
        '-d',
        '--delim',
        default='\t',
        help='Delimiter used for the statistics output.')
    parser.add_argument(
        '-o',
        '--output',
        default=sys.stdout,
        type=argparse.FileType('w'),
        help='Save the statistics into a file.')
    parser.add_argument(
        '-p',
        '--permission',
        help='Prints out all extension names and descriptions that use the given permission.'
    )
    parser.add_argument(
        '-c',
        '--categories',
        action='store_true',
        help='Print the results for each category separately.')

    args = parser.parse_args()

    category_folders = [args.dir]
    if args.categories:
        category_folders += [
            os.path.join(args.dir, d) for d in next(os.walk(args.dir))[1]
        ]

    for category_folder in category_folders:
        args.output.write('Results for category {}:\n\n'.format(
            category_folder))
        if args.permission:
            handlers = [PermissionHandlerPrintNames(args.permission)]
        else:
            handlers = [PermissionHandler(), PermissionHandlerCondensed()]
        PermissionStatisticGenerator.run(category_folder, handlers)

        for handler in handlers:
            handler.print_result(args.output, args.delim)
