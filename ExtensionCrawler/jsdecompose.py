#!/usr/bin/env python3
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
"""Python analys providing a decomposition analysis of JavaScript code in
   general and Chrome extensions in particular."""

import os
import re
import json
from enum import Enum
import hashlib

class DetectionType(Enum):
    """Enumeration for detection types."""
    FILENAME = 1
    FILECONTENT = 2
    FILENAME_FILECONTENT = 3
    URL = 4
    HASH = 5

class FileClassification(Enum):
    """ Enumeration for file classification"""
    LIBRARY = 1
    LIKELY_LIBRARY = 2
    APPLICATION = 3

def lib_identifiers():
    """Initialize identifiers for known libraries from JSON file."""
    regex_file = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../resources/',
        'js_identifier.json')
    with open(regex_file, 'r') as json_file:
        json_content = json_file.read()
    return json.loads(json_content)


def unknown_filename_identifier():
    """Identifier for extracting version information from unknown/generic file names."""
    return re.compile(
        r'(.+)[\-\_]([0-9]{1,2}[\.|\-|\_][0-9a-z]{1,2}[\.|\-|\_][0-9a-z\-\_]*)',
        re.IGNORECASE)


def lib_isin_list(lib, ver, lib_list):
    """Check if a specific library/version has already been detected."""
    for item in lib_list:
        if (item['lib'].lower() == lib.lower() and
                item['ver'].lower() == ver.lower()):
            return True
    return False


def unknown_lib_identifiers():
    """List of identifiers for generic library version headers."""
    return ([
        re.compile(
            rb'[\/|\/\/|\s]\*?\s?([a-zA-Z0-9\.]+)\sv?([0-9][\.|\-|\_][0-9.a-z_\\\\-]+)',
            re.IGNORECASE
        ),  #MatchType: name version, e.g. mylib v1.2.9b or mylib.anything 1.2.8
        re.compile(
            rb'[\/|\/\/|\s]\*?\s?([a-zA-Z0-9\.]+)\s(?: version)\:?\s?v?([0-9][0-9.a-z_\\\\-]+)',
            re.IGNORECASE
        ),  #MatchType: name version: ver, e.g. mylib version: v1.2.9, or mylib.js version 1.2.8
        re.compile(
            rb'\@*(version)\s?[\:|-]?\s?v?([0-9][\.|\-|\_][0-9.a-z_\\\\-]+)',
            re.IGNORECASE
        ),  #MatchType: version x.x.x, e.g. @version: 1.2.5 or version - 1.2.5 etc.
        re.compile(
            rb'(version)[\:|\=]\s?.?([0-9]{1,2}[\.|\-|\_][0-9.a-z_\\\\-]+).?',
            re.IGNORECASE),
        re.compile(rb'(.+) v([0-9]{1,2}[\.|\-|\_][0-9]{1,2}[0-9.a-z_\\\\-]*)',
                   re.IGNORECASE)
    ])


def init_jsinfo(zipfile, js_file):
    """Initialize jsinfo record."""
    data = ""
    with zipfile.open(js_file) as js_file_obj:
        data = js_file_obj.read()
    js_info = {
        'lib': None,
        'ver': None,
        'detectMethod': None,
        'type': None,
        'evidenceStartLine': None,
        'evidenceEndLine': None,
        'evidenceText': None,
        'jsFilename': os.path.basename(js_file.filename),
        'md5': hashlib.md5(data).hexdigest(),
        'size': int(js_file.file_size),
        'path': js_file.filename
    }
    return js_info


def analyse_known_filename(zipfile, js_file):
    """Check for known file name patterns."""
    libs = list()
    for lib, regex in lib_identifiers().items():
        if 'filename' in regex:
            filename_matched = re.search(regex['filename'],
                                         js_file.filename, re.IGNORECASE)
            if filename_matched:
                js_info = init_jsinfo(zipfile, js_file)
                js_info['lib'] = lib
                js_info['ver'] = filename_matched.group(2)
                js_info['type'] = FileClassification.LIBRARY
                js_info['detectMethod'] = DetectionType.FILENAME
                libs.append(js_info)
    return libs

def analyse_known_filecontent(zipfile, js_file):
    """Check for known file content (license headers)."""
    libs = list()
    data = ""
    with zipfile.open(js_file) as js_file_obj:
        data = js_file_obj.read()
    for lib, regex in lib_identifiers().items():
        if 'filecontent' in regex:
            #iterate over the filecontent regexes for this  to see if it has a match
            for file_content in regex['filecontent']:
                lib_matched = re.finditer(file_content.encode(), data,
                                          re.IGNORECASE)
                for match in lib_matched:
                    ver = match.group(2).decode()
                    js_info = init_jsinfo(zipfile, js_file)
                    js_info['lib'] = lib
                    js_info['ver'] = ver
                    js_info['type'] = FileClassification.LIBRARY
                    js_info['detectMethod'] = DetectionType.FILECONTENT
                    libs.append(js_info)
    return libs

def analyse_generic_filename(zipfile, js_file):
    """Check for generic file name patterns."""
    libs = list()
    unknown_filename_match = unknown_filename_identifier().search(
        js_file.filename)
    if unknown_filename_match:
        js_info = init_jsinfo(zipfile, js_file)
        js_info['lib'] = unknown_filename_match.group(1)
        js_info['ver'] = unknown_filename_match.group(2)
        js_info['type'] = FileClassification.LIKELY_LIBRARY
        js_info['detectMethod'] = DetectionType.FILENAME
        libs.append(js_info)
    return libs

def analyse_generic_filecontent(zipfile, js_file):
    """Check for generic file content (license headers)."""
    libs = list()
    data = ""
    with zipfile.open(js_file) as js_file_obj:
        data = js_file_obj.read()
    for unkregex in unknown_lib_identifiers():
        unkown_lib_matched = unkregex.finditer(data)
        for match in unkown_lib_matched:
            js_info = init_jsinfo(zipfile, js_file)
            js_info['lib'] = ((js_file.filename).replace(
                '.js', '')).replace('.min', '')
            js_info['ver'] = match.group(2).decode()
            js_info['detectMethod'] = DetectionType.FILENAME_FILECONTENT
            js_info['type'] = FileClassification.LIKELY_LIBRARY
            libs.append(js_info)
    return libs

def analyse_filename(zipfile, js_file):
    """Check for file name patterns of libraries (known and generic as fall back)`"""
    res = analyse_known_filename(zipfile, js_file)
    if not res:
        res = analyse_generic_filecontent(zipfile, js_file)
    return res

def decompose_js(zipfile):
    """JavaScript decomposition analysis for extensions."""
    def remdups(lst):
        """Remove duplicates in a list."""
        res = list()
        for sublist in lst:
            if sublist not in res:
                res.append(sublist)
        return res

    js_inventory = []
    for js_file in list(filter(lambda x: x.filename.endswith(".js"), zipfile.infolist())):
        
        js_info_file = analyse_filename(zipfile, js_file)

        js_info_file += analyse_generic_filecontent(zipfile, js_file)
        js_info_file += analyse_known_filecontent(zipfile, js_file)

        if not js_info_file:
            # if no library could be detected, we report the JavaScript file as 'application'.
            js_info = init_jsinfo(zipfile, js_file)
            js_info['lib'] = None
            js_info['ver'] = None
            js_info['detectMethod'] = None
            js_info['type'] = FileClassification.APPLICATION
            js_inventory.append(js_info)
        else:
            js_inventory += js_info_file

    return remdups(js_inventory)
