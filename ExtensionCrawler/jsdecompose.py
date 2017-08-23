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


def InitLibIdentifiers():
    ##Class variables- whose values are shared among 'all' instances of this 'class'
    regexFile = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../resources/',
        'js_identifier.json')  ##full path

    with open(regexFile, 'r') as fObject:
        #read the whole file content as a string
        jString = fObject.read()

    return json.loads(jString)


def InitUnknownFilenameIdentifier():
    return re.compile(
        r'(.+)[\-\_]([0-9]{1,2}[\.|\-|\_][0-9a-z]{1,2}[\.|\-|\_][0-9a-z\-\_]*)',
        re.IGNORECASE)


def isLibExistInList(lib, ver, listOfDict):
    for item in listOfDict:
        if (item['lib'].lower() == lib.lower() and
                item['ver'].lower() == ver.lower()):
            return True
    return False


def InitUnknownLibraryIdentifier():
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
    DetectionType = Enum("DetectionType",
                         'FILENAME FILECONTENT FILENAME_FILECONTENT URL HASH')
    identifiedKnLibrariesList = []
    identifiedUnknownLibrariesDict = {}
    identifiedUnLibrariesList = []
    identifiedApplicationsList = []

    libraryIdentifiers = InitLibIdentifiers()
    unknownFilenameIdentifier = InitUnknownFilenameIdentifier()
    unknownLibraryIdentifier = InitUnknownLibraryIdentifier()

    jsFiles = list(
        filter(lambda x: x.filename.endswith(".js"), zipfile.infolist()))

    #for each jsFile path in the list
    for jsFile in list(jsFiles):
        #check whether the file is empty

        isApplication = True
        with zipfile.open(jsFile) as fObject:
            data = fObject.read()
            md5 = hashlib.md5(data).hexdigest()

            libraryIdentified = False

            #iterate over the library regexes, to check whether it has a match
            for lib, regex in libraryIdentifiers.items():
                ##METHOD_1: Read the filename of this file
                #if it matches to one of the defined filename regex, store in the dict
                #check if there is a filename regex exists for this lib
                if 'filename' in regex:
                    filenameMatched = re.search(regex['filename'],
                                                jsFile.filename, re.IGNORECASE)

                    if filenameMatched:
                        #check whether this lib has already been identified in the dict, otherwise store the libname and version from the filename
                        ver = filenameMatched.group(2)
                        identifiedKnLibrariesList.append({
                            'lib': lib,
                            'ver': ver,
                            'detectMethod': DetectionType.FILENAME.name,
                            'jsFilename': os.path.basename(jsFile),
                            'md5': md5,
                            'size': int(jsFile.file_size),
                            'path': jsFile.filename
                        })
                        libraryIdentified = True
                        isApplication = False

                ##METHOD_2: Check content of every .js file
                #check if there is filecontent regex exists for this lib
                if 'filecontent' in regex:
                    #iterate over the filecontent regexes for this lib to see if it has a match
                    for aFilecontent in regex['filecontent']:
                        libraryMatched = re.search(aFilecontent.encode(), data,
                                                   re.IGNORECASE)
                        if (libraryMatched):
                            ver = libraryMatched.group(2).decode()
                            if (not isLibExistInList(
                                    lib, ver, identifiedKnLibrariesList)):
                                #to be safe, check if the version in the filename, matches with the filecontent
                                identifiedKnLibrariesList.append({
                                    'lib': lib,
                                    'ver': ver,
                                    'detectMethod':
                                    DetectionType.FILECONTENT.name,
                                    'jsFilename': os.path.basename(jsFile),
                                    'md5': md5,
                                    'size': int(jsFile.file_size),
                                    'path': jsFile.filename
                                })

                            libraryIdentified = True
                            isApplication = False
                            break
                            #do not need to check the other regex for this library - since its already found

                        #if none of the regexes in the repository match, check whether the unknown regexes match
            if not libraryIdentified:
                #check the filename
                unkFilenameMatch = unknownFilenameIdentifier.search(
                    jsFile.filename)
                if unkFilenameMatch:
                    identifiedUnLibrariesList.append({
                        'lib': unkFilenameMatch.group(1),
                        'ver': unkFilenameMatch.group(2),
                        'detectMethod': DetectionType.FILENAME.name,
                        'type': "library",
                        'jsFilename': os.path.basename(jsFile.filename),
                        'md5': md5,
                        'size': int(jsFile.file_size),
                        'path': jsFile.filename
                    })
                    isApplication = False
                    continue
                    #do not need to check the filecontent

                #otherwise check the filecontent
                for unkregex in unknownLibraryIdentifier:
                    #print("Analysing for regex: {}".format(unkregex))
                    unknownLibraryMatched = unkregex.search(data)
                    if unknownLibraryMatched:
                        #check whether this library is actually unknown, by comparing it with identified dicts
                        #unkLib = unknownLibraryMatched.group(1).lower().decode()
                        unkVer = unknownLibraryMatched.group(2).decode()
                        unkjsFile = ((jsFile.filename).replace(
                            '.js', '')).replace('.min', '')

                        if (not isLibExistInList(unkjsFile, unkVer,
                                                 identifiedKnLibrariesList)):
                            #put this unknown library in the unknown dictionary. use the filename instead - safer
                            identifiedUnLibrariesList.append({
                                'lib': unkjsFile,
                                'ver': unkVer,
                                'detectMethod':
                                DetectionType.FILENAME_FILECONTENT.name,
                                'type': "likely_library",
                                'jsFilename':
                                os.path.basename(jsFile.filename),
                                'md5': md5,
                                'size': int(jsFile.file_size),
                                'path': jsFile.filename
                            })
                        isApplication = False
                        break
                        #do not need to check the rest of the unknown regexes

                    #if none of the above regexes match, then it is likely an application
        if isApplication:
            identifiedApplicationsList.append({
                'lib': None,
                'ver': None,
                'detectMethod': None,
                'type': "application",
                'jsFilename': os.path.basename(jsFile.filename),
                'md5': md5,
                'size': int(jsFile.file_size),
                'path': jsFile.filename
            })

    return (identifiedKnLibrariesList + identifiedUnLibrariesList +
            identifiedApplicationsList)
