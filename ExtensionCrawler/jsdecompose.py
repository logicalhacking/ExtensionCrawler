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

def detectLibraries(zipfile):
    """JavaScript decomposition analysis for extensions."""
    detection_type = Enum("DetectionType",
                          'FILENAME FILECONTENT FILENAME_FILECONTENT URL HASH')
    known_libs = []
    unkown_libs = []
    identifiedApplicationsList = []

    js_files = list(
        filter(lambda x: x.filename.endswith(".js"), zipfile.infolist()))

    for js_file in js_files:
        is_app_js = True
        data = ""
        with zipfile.open(js_file) as js_file_obj:
            data = js_file_obj.read()

        js_info = {'lib': None,
                   'ver': None,
                   'detectMethod': None,
                   'type': None,
                   'jsFilename': os.path.basename(js_file.filename),
                   'md5': hashlib.md5(data).hexdigest(),
                   'size': int(js_file.file_size),
                   'path': js_file.filename
                  }

        lib_identified = False

        #iterate over the library regexes, to check whether it has a match
        for lib, regex in lib_identifiers().items():
            ##METHOD_1: Read the filename of this file
            #if it matches to one of the defined filename regex, store in the dict
            #check if there is a filename regex exists for this lib
            if 'filename' in regex:
                filenameMatched = re.search(regex['filename'],
                                            js_file.filename, re.IGNORECASE)

                if filenameMatched:
                    #check whether this lib has already been identified in the dict, otherwise store the libname and version from the filename
                    js_info['lib'] = lib
                    js_info['ver'] = filenameMatched.group(2)
                    js_info['type'] = "library"
                    js_info['detectMethod'] = detection_type.FILENAME.name
                    known_libs.append(js_info)
                    lib_identified = True
                    is_app_js = False

            ##METHOD_2: Check content of every .js file
            #check if there is filecontent regex exists for this lib
            if 'filecontent' in regex:
                #iterate over the filecontent regexes for this  to see if it has a match
                for aFilecontent in regex['filecontent']:
                    libraryMatched = re.search(aFilecontent.encode(), data,
                                               re.IGNORECASE)
                    if libraryMatched:
                        ver = libraryMatched.group(2).decode()
                        if (not lib_isin_list(
                                lib, ver, known_libs)):
                            js_info['lib'] = lib
                            js_info['ver'] = ver
                            js_info['type'] = "library"
                            js_info['detectMethod'] = detection_type.FILECONTENT.name
                            known_libs.append(js_info)       

                        lib_identified = True
                        is_app_js = False
                        break
                        #do not need to check the other regex for this library - since its already found

                    #if none of the regexes in the repository match, check whether the unknown regexes match
        if not lib_identified:
            #check the filename
            unkFilenameMatch = unknown_filename_identifier().search(
                js_file.filename)
            if unkFilenameMatch:
                js_info['lib'] = unkFilenameMatch.group(1)
                js_info['ver'] = unkFilenameMatch.group(2)
                js_info['type'] = "likely_library"
                js_info['detectMethod'] = detection_type.FILENAME.name
                unkown_libs.append(js_info)
                is_app_js = False
                continue
                #do not need to check the filecontent

            #otherwise check the filecontent
            for unkregex in unknown_lib_identifiers():
                #print("Analysing for regex: {}".format(unkregex))
                unknownLibraryMatched = unkregex.search(data)
                if unknownLibraryMatched:
                    #check whether this library is actually unknown, by comparing it with identified dicts
                    #unkLib = unknownLibraryMatched.group(1).lower().decode()
                    unkVer = unknownLibraryMatched.group(2).decode()
                    unkjsFile = ((js_file.filename).replace(
                        '.js', '')).replace('.min', '')

                    if (not lib_isin_list(unkjsFile, unkVer,
                                          known_libs)):
                        #put this unknown library in the unknown dictionary. use the filename instead - safer
                        js_info['lib'] = unkjsFile
                        js_info['ver'] = unkVer
                        js_info['detectMethod'] = detection_type.FILENAME_FILECONTENT.name
                        js_info['type'] = "likely_library"
                        unkown_libs.append(js_info)
                    is_app_js = False
                    break
                    #do not need to check the rest of the unknown regexes

                #if none of the above regexes match, then it is likely an application
        if is_app_js:
            js_info['lib'] = None
            js_info['ver'] = None
            js_info['detectMethod'] = None
            js_info['type'] = "application"
            identifiedApplicationsList.append(js_info)

    return (known_libs + unkown_libs +
            identifiedApplicationsList)
