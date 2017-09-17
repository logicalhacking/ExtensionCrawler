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
"""Python analys providing a decomposition analysis of JavaScript code in
   general and Chrome extensions in particular."""

import os
import io
import re
import json
from enum import Enum
from ExtensionCrawler.js_mincer import mince_js
from ExtensionCrawler.file_identifiers import get_file_identifiers

class DetectionType(Enum):
    """Enumeration for detection types."""
    # EMPTY_FILE
    FILE_SIZE = "file_size"
    # LIBRARY 
    SHA1 = "sha1"
    MD5 = "md5"
    SHA1_DECOMPRESSED = "sha1 (after decompression)"
    MD5_DECOMPRESSED = "md5 (after decompression)"
    SHA1_NORMALIZED = "sha1 (after normalization)"
    MD5_NORMALIZED = "md5 (after normalization)"
    SHA1_DECOMPRESSED_NORMALIZED = "sha1 (after decompression and normalization)"
    MD5_DECOMPRESSED_NORMALIZED = "md5 (after decompression and normalization)"
    # VERY_LIKELY_LIBRARY
    FILENAME_COMMENTBLOCK = "filename and witness in comment block"
    FILENAME_CODEBLOCK = "filename and witness in code block"
    # LIKELY_LIBRARY
    COMMENTBLOCK = "witness in comment block"
    CODEBLOCK = "witness in code block"
    FILENAME = "known file name"
    URL = "known URL"
    # LIKELY_APPLICATION
    DEFAULT = "default"
    
class FileClassification(Enum):
    """ Enumeration for file classification"""
    EMPTY_FILE = "other (empty file)"
    LIBRARY = "known library"
    VERY_LIKELY_LIBRARY = "very likely known library"
    LIKELY_LIBRARY = "likely known library"
    LIKELY_APPLICATION = "likely application"

def load_lib_identifiers():
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

def unknown_lib_identifiers():
    """List of identifiers for generic library version headers."""
    return ([
        re.compile(
            r'[\/|\/\/|\s]\*?\s?([a-zA-Z0-9\.]+)\sv?([0-9][\.|\-|\_][0-9.a-z_\\\\-]+)',
            re.IGNORECASE
        ),  #MatchType: name version, e.g. mylib v1.2.9b or mylib.anything 1.2.8
        re.compile(
            r'[\/|\/\/|\s]\*?\s?([a-zA-Z0-9\.]+)\s(?: version)\:?\s?v?([0-9][0-9.a-z_\\\\-]+)',
            re.IGNORECASE
        ),  #MatchType: name version: ver, e.g. mylib version: v1.2.9, or mylib.js version 1.2.8
        re.compile(
            r'\@*(version)\s?[\:|-]?\s?v?([0-9][\.|\-|\_][0-9.a-z_\\\\-]+)',
            re.IGNORECASE
        ),  #MatchType: version x.x.x, e.g. @version: 1.2.5 or version - 1.2.5 etc.
        re.compile(
            r'(version)[\:|\=]\s?.?([0-9]{1,2}[\.|\-|\_][0-9.a-z_\\\\-]+).?',
            re.IGNORECASE),
        re.compile(r'(.+) v([0-9]{1,2}[\.|\-|\_][0-9]{1,2}[0-9.a-z_\\\\-]*)',
                   re.IGNORECASE)
    ])


def init_jsinfo(zipfile, js_file):
    """Initialize jsinfo record."""
    data = ""
    if zipfile is not None:
        with zipfile.open(js_file) as js_file_obj:
            data = js_file_obj.read()
            js_filename = os.path.basename(js_file.filename)
            file_size = int(js_file.file_size)
            path = js_file.filename
    else:
        with open(js_file, mode='rb') as js_file_obj:
            data = js_file_obj.read()
            js_filename = os.path.basename(js_file)
            file_size = len(data)
            path = js_file

    js_info = get_file_identifiers(path, data)
    js_info['lib'] = None
    js_info['jsFilename'] = js_info['filename']
    js_info['version'] = None
    js_info['detectionMethod'] = None
    js_info['detectionMethodDetails'] = None
    js_info['type'] = None
    js_info['evidenceStartPos'] = None
    js_info['evidenceEndPos'] = None
    js_info['evidenceText'] = None
    if js_info['size'] == 0:
        js_info['detectionMethod'] = DetectionType.FILE_SIZE
        js_info['type'] = FileClassification.EMPTY_FILE

    return js_info

def analyse_checksum(zipfile, js_file, js_info):
    """Check for known md5 hashes (file content)."""
    json_data = load_lib_identifiers()
    for lib in json_data:
        for info in json_data[lib]:
            if info == 'sha1':
                for lib_file in json_data[lib]['sha1']:
                    if lib_file['sha1'].lower() == js_info['sha1'].hex():
                        js_info['lib'] = lib
                        js_info['version'] = lib_file['version']
                        js_info['type'] = FileClassification.LIBRARY
                        js_info['detectionMethod'] = DetectionType.SHA1,
                        if 'comment' in lib_file:
                            js_info['detectionMethodDetails'] = lib_file['comment']
                        return [js_info]
            if info == 'md5':
                for lib_file in json_data[lib]['md5']:
                    if lib_file['md5'].lower() == js_info['md5'].hex():
                        js_info['lib'] = lib
                        js_info['version'] = lib_file['version']
                        js_info['type'] = FileClassification.LIBRARY
                        js_info['detectionMethod'] = DetectionType.MD5
                        if 'comment' in lib_file:
                            js_info['detectionMethodDetails'] = lib_file['comment']
                        return [js_info]
    return None



def analyse_known_filename(zipfile, js_file, js_info):
    """Check for known file name patterns."""
    libs = list()
    for lib, regex in load_lib_identifiers().items():
        if 'filename' in regex:
            if zipfile is not None:
                filename = js_file.filename
            else:
                filename = js_file
            filename_matched = re.search(regex['filename'],
                                         filename, re.IGNORECASE)
            if filename_matched:
                js_info['lib'] = lib
                js_info['version'] = filename_matched.group(2)
                js_info['type'] = FileClassification.LIBRARY
                js_info['detectionMethod'] = DetectionType.FILENAME
                js_info['detectionMethodDetails'] = regex['filename']
                libs.append(js_info)
    return libs

def analyse_generic_filename(zipfile, js_file, js_info):
    """Check for generic file name patterns."""
    libs = list()
    if zipfile is not None:
        filename = js_file.filename
    else:
        filename = js_file

    unknown_filename_match = unknown_filename_identifier().search(
        filename)
    if unknown_filename_match:
        js_info['lib'] = os.path.basename(unknown_filename_match.group(1)).replace(
                        '.js', '').replace('.min', '')
        js_info['version'] = unknown_filename_match.group(2)
        js_info['type'] = FileClassification.LIKELY_LIBRARY
        js_info['detectionMethod'] = DetectionType.FILENAME
        libs.append(js_info)
    return libs

def analyse_filename(zipfile, js_file, js_info):
    """Check for file name patterns of libraries (known and generic as fall back)`"""
    res = analyse_known_filename(zipfile, js_file, js_info)
    if not res:
        res = analyse_generic_filename(zipfile, js_file, js_info)
    return res


def analyse_comment_known_libs(zipfile, js_file, js_info, comment):
    """Search for library specific identifiers in comment block."""
    libs = list()
    if zipfile is not None:
        filename = js_file.filename
    else:
        filename = js_file
    for lib, regex in load_lib_identifiers().items():
        if('filecontent' in regex):
            for unkregex in regex['filecontent']:
                unkown_lib_matched = unkregex.finditer(comment.content)
                for match in unkown_lib_matched:
                    js_info['lib'] = lib
                    js_info['version'] = match.group(2)
                    js_info['detectionMethod'] = DetectionType.COMMENTBLOCK
                    js_info['detectionMethodDetails'] = unkregex
                    js_info['type'] = FileClassification.LIBRARY
                    libs.append(js_info)
    return libs

def analyse_comment_generic_libs(zipfile, js_file, js_info, comment):
    """Search for generic identifiers in comment block."""
    libs = list()
    if zipfile is not None:
        filename = js_file.filename
    else:
        filename = js_file

    for unkregex in unknown_lib_identifiers():
        unkown_lib_matched = unkregex.finditer(comment.content)
        for match in unkown_lib_matched:
            js_info['lib'] = ((os.path.basename(filename)).replace(
                '.js', '')).replace('.min', '')
            js_info['version'] = match.group(2)
            js_info['detectionMethod'] = DetectionType.COMMENTBLOCK
            js_info['detectionMethodDetails'] = unkregex
            js_info['type'] = FileClassification.LIKELY_LIBRARY
            libs.append(js_info)
    return libs

def analyse_comment_blocks(zipfile, js_file, js_info):
    """Search for library identifiers in comment."""
    def mince_js_fileobj(js_text_file_obj):
        """Mince JavaScript file using a file object."""
        libs = list()
        for block in mince_js(js_text_file_obj, single_line_comments_block=True):
            block_libs = list()
            if block.is_comment():
                block_libs = analyse_comment_known_libs(zipfile, js_file, js_info, block)
                if block_libs is None:
                    block_libs = analyse_comment_generic_libs(zipfile, js_file, js_info, block)
                if block_libs is not None:
                    libs += block_libs
        return libs
    libs = []
    try:
        if zipfile is not None:
            with zipfile.open(js_file) as js_file_obj:
                with io.TextIOWrapper(js_file_obj, js_info['encoding']) as js_text_file_obj:
                    libs = mince_js_fileobj(js_text_file_obj)
        else:
            with open(js_file) as js_text_file_obj:
                libs = mince_js_fileobj(js_text_file_obj)
    except:
        libs = list()
    return libs

def decompose_js(file):
    """JavaScript decomposition analysis for extensions."""
    def remdups(lst):
        """Remove duplicates in a list."""
        res = list()
        for sublist in lst:
            if sublist not in res:
                res.append(sublist)
        return res

    zipfile = None
    js_inventory = []
    if isinstance(file, str):
        js_files = [file]
    else:
        zipfile = file
        js_files = list(filter(lambda x: x.filename.endswith(".js"), zipfile.infolist()))

    for js_file in js_files:
        js_info = init_jsinfo(zipfile, js_file)

        if js_info['type'] == FileClassification.EMPTY_FILE:
            js_inventory.append(js_info)
        else:
            js_info_file = analyse_checksum(zipfile, js_file, js_info)
            if not js_info_file:
                js_info_file = analyse_filename(zipfile, js_file, js_info)
                js_info_file += analyse_comment_blocks(zipfile, js_file, js_info)
            if not js_info_file:
                # if no library could be detected, we report the JavaScript file as 'application'.
                js_info['lib'] = None
                js_info['version'] = None
                js_info['detectionMethod'] = DetectionType.DEFAULT
                js_info['type'] = FileClassification.LIKELY_APPLICATION
                js_inventory.append(js_info)
            else:
                js_inventory += js_info_file

    return remdups(js_inventory)
