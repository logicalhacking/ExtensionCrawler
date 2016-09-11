#!/usr/bin/env python3
from zipfile import ZipFile
import argparse
import json
import sys
import os
from jsmin import jsmin
import re

regex_concrete_url = re.compile(r'^.*://.*[a-z0-9]+\.[a-z]+.*$')

def condense(permissions):
    concrete_url_perms = {}
    other_perms = {}
    for perm in permissions:
        if regex_concrete_url.match(perm):
            concrete_url_perms[perm] = permissions[perm]
        else:
            other_perms[perm] = permissions[perm]
    other_perms["CONCRETE_URLS"] = sum([concrete_url_perms[perm] for perm in concrete_url_perms])
    return other_perms
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Prints statistics about the requested permissions of downloaded extensions.')
    parser.add_argument('dir', help='The directory in which the extensions are stored. The directory structure must be {category}/{extid}/*.crx.')
    parser.add_argument('-d', '--delim', default='\t', help='Delimiter used for the statistics output.')
    parser.add_argument('-o', '--output', default='-', help='Save the statistics into a file.')
    parser.add_argument('-c', '--condensed', action="store_true", help='Only print statistics where concrete URLs are condensed into one permission.')
    
    args = parser.parse_args()

    if args.output is not '-':
        os.remove(args.output)

    category_folders  = [args.dir]
    category_folders += [os.path.join(args.dir, d) for d in next(os.walk(args.dir))[1]]

    for category_folder in category_folders:    
        permissions = {}
        nrexts = 0

        for root, dirs, files in os.walk(category_folder):
            crxfile = next((f for f in files if f.endswith('.crx')), None)
            if crxfile:
                nrexts += 1
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
                                perm = str(permobj)
                                if not perm in permissions:
                                    permissions[perm] = 0
                                permissions[perm] += 1
        f = open(args.output, 'a') if args.output is not '-' else sys.stdout
        f.write('Permissions in category {} ({} extensions)\n\n'.format(os.path.basename(category_folder), nrexts))
        if not args.condensed:
            for perm in sorted(permissions, key=permissions.get, reverse=True):
                f.write('{}{}{}{}{:.2%}\n'.format(perm, args.delim, permissions[perm], args.delim, float(permissions[perm]) / nrexts))
            f.write('\n')

        condensed_permissions = condense(permissions)
        f.write('Condensed\n')
        for perm in sorted(condensed_permissions, key=condensed_permissions.get, reverse=True):
            f.write('{}{}{}{}{:.2%}\n'.format(perm, args.delim, condensed_permissions[perm], args.delim, float(condensed_permissions[perm]) / nrexts))
        f.write('\n')

        if f is not sys.stdout:
            f.close()
