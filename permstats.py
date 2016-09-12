#!/usr/bin/env python3
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
        if str(permobj) == self.permname:
            with open(os.path.join(path, 'metadata.json')) as f:
                metadata = json.load(f)
                self.extinfo[extid] = '{} | {} | {}'.format(metadata[1], metadata[6], extid)
    def print_result(self, fileobj, delim):
        fileobj.write('Extensions that use permission "{}":\n\n'.format(self.permname))
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
        for perm in sorted(self.permissions, key=self.permissions.get, reverse=True):
            fileobj.write('{}{}{}{}{:.2%}\n'.format(perm, delim, self.permissions[perm], delim, float(self.permissions[perm]) / len(self.extids)))
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
        fileobj.write('Condensed. Total: {} extensions\n'.format(len(self.extids)))
        for perm in sorted(self.permissions, key=self.permissions.get, reverse=True):
            fileobj.write('{}{}{}{}{:.2%}\n'.format(perm, delim, self.permissions[perm], delim, float(self.permissions[perm]) / len(self.extids)))
        fileobj.write('\n\n')

    #condensed_permissions = condense(permissions)
    #args.output.write('Condensed\n')
    #for perm in sorted(condensed_permissions, key=condensed_permissions.get, reverse=True):
    #    args.output.write('{}{}{}{}{:.2%}\n'.format(perm, args.delim, condensed_permissions[perm], args.delim, float(condensed_permissions[perm]) / nrexts))
    #args.output.write('\n')
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
                                    handler.handle_permission(extid, permobj, root)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prints statistics about the requested permissions of downloaded extensions.')
    parser.add_argument('dir', help='The directory in which the extensions are stored. The directory structure must be {category}/{extid}/*.crx.')
    parser.add_argument('-d', '--delim', default='\t', help='Delimiter used for the statistics output.')
    parser.add_argument('-o', '--output', default=sys.stdout, type=argparse.FileType('w'), help='Save the statistics into a file.')
    parser.add_argument('-p', '--permission', help='Prints out all extension names and descriptions that use the given permission.')
    
    args = parser.parse_args()

    category_folders  = [args.dir]
    category_folders += [os.path.join(args.dir, d) for d in next(os.walk(args.dir))[1]]

    for category_folder in category_folders:    
        args.output.write('Permissions for category {}:\n\n'.format(category_folder))
        if args.permission:
            handlers = [PermissionHandlerPrintNames(args.permission)]
        else:
            handlers = [PermissionHandler(), PermissionHandlercondensed()]
        PermissionStatisticGenerator.run(category_folder, handlers)

        for handler in handlers:
            handler.print_result(args.output, args.delim)
