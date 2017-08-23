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
import mmap
from enum import Enum


class Extension:
    ##Class variables- whose values are shared among 'all' instances of this 'class'
    regexFile = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '../resources/',
        'js_identifier.json')  ##full path

    with open(regexFile, 'r') as fObject:
        #read the whole file content as a string
        jString = fObject.read()

    libraryIdentifiers = json.loads(jString)

    unknownFilenameIdentifier = re.compile(
        r'(.+)[\-\_]([0-9]{1,2}[\.|\-|\_][0-9a-z]{1,2}[\.|\-|\_][0-9a-z\-\_]*)',
        re.IGNORECASE)

    #this will be used, when no known library is found
    unknownLibraryIdentifier = [
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
    ]

    #if even the generic regex is not matched, check if the line contains the string "version"
    #versionOnlyIdentifier =

    DetectionType = Enum("DetectionType",
                         'FILENAME FILECONTENT FILENAME_FILECONTENT URL HASH')

    #Class constructor initialiser - is called when a new instance of this class is created
    def __init__(self, path):
        #check if the path is a directory
        if not os.path.isdir(path):
            print("This is not a valid path: " + path)
            return

        self.extensionPath = path
        self.jsFiles = [
        ]  #to store all the js files in this extension instance
        self.identifiedLibrariesDict = {}
        self.identifiedKnLibrariesList = []
        self.identifiedUnknownLibrariesDict = {}
        self.identifiedUnLibrariesList = []
        self.identifiedApplicationsList = []

    ##public class instance methods
    #these are instance level methods - so any changes will effect that instance only
    def __getJsFilePaths(self):
        #loop through every element within that path
        for (dirpath, dirname, filenames) in os.walk(self.extensionPath):
            ##loop through filenames
            for aFile in filenames:
                #check if a file is a .js file
                if aFile.endswith('.js'):
                    self.jsFiles.append(os.path.join(dirpath, aFile))

    #returns 3 items - a list of dictionary, a list of dictionary, a list
    def detectLibraries(self):
        #get the list of jsFiles in this extension
        self.__getJsFilePaths()

        #for each jsFile path in the list
        for jsFile in self.jsFiles:
            #check whether the file is empty
            if os.path.getsize(jsFile) == 0:
                #print("Empty file: " + jsFile)
                continue

            isApplication = True
            with open(jsFile, 'r+') as fObject:
                data = mmap.mmap(fObject.fileno(), 0)
                libraryIdentified = False

                #iterate over the library regexes, to check whether it has a match
                for lib, regex in Extension.libraryIdentifiers.items():
                    ##METHOD_1: Read the filename of this file
                    #if it matches to one of the defined filename regex, store in the dict
                    #check if there is a filename regex exists for this lib
                    if 'filename' in regex:
                        filenameMatched = re.search(regex['filename'],
                                                    os.path.basename(jsFile),
                                                    re.IGNORECASE)

                        if filenameMatched:
                            #check whether this lib has already been identified in the dict, otherwise store the libname and version from the filename
                            #if(lib not in self.identifiedLibrariesDict):
                            ver = filenameMatched.group(2)
                            #self.identifiedLibrariesDict[lib] = {'ver':ver, 'detectMethod': self.DetectionType.FILENAME.name, 'path':jsFile}
                            self.identifiedKnLibrariesList.append({
                                'lib': lib,
                                'ver': ver,
                                'detectMethod':
                                self.DetectionType.FILENAME.name,
                                'jsFilename': os.path.basename(jsFile),
                                'path': jsFile
                            })
                            libraryIdentified = True
                            isApplication = False

                    ##METHOD_2: Check content of every .js file
                    #check if there is filecontent regex exists for this lib
                    if 'filecontent' in regex:
                        #iterate over the filecontent regexes for this lib to see if it has a match
                        for aFilecontent in regex['filecontent']:
                            libraryMatched = re.search(aFilecontent.encode(),
                                                       data, re.IGNORECASE)
                            if (libraryMatched):
                                ver = libraryMatched.group(2).decode()
                                if (not self.isLibExistInList(
                                        lib, ver,
                                        self.identifiedKnLibrariesList)):
                                    #to be safe, check if the version in the filename, matches with the filecontent
                                    self.identifiedKnLibrariesList.append({
                                        'lib': lib,
                                        'ver': ver,
                                        'detectMethod':
                                        self.DetectionType.FILECONTENT.name,
                                        'jsFilename': os.path.basename(jsFile),
                                        'path': jsFile
                                    })

                                libraryIdentified = True
                                isApplication = False
                                break
                                #do not need to check the other regex for this library - since its already found

                #if none of the regexes in the repository match, check whether the unknown regexes match
                if not libraryIdentified:
                    #check the filename
                    unkFilenameMatch = self.unknownFilenameIdentifier.search(
                        os.path.basename(jsFile))
                    if unkFilenameMatch:
                        self.identifiedUnLibrariesList.append({
                            'lib': unkFilenameMatch.group(1),
                            'ver': unkFilenameMatch.group(2),
                            'detectMethod': self.DetectionType.FILENAME.name,
                            'jsFilename': os.path.basename(jsFile),
                            'path': jsFile
                        })
                        isApplication = False
                        continue
                        #do not need to check the filecontent

                    #otherwise check the filecontent
                    for unkregex in Extension.unknownLibraryIdentifier:
                        #print("Analysing for regex: {}".format(unkregex))
                        unknownLibraryMatched = unkregex.search(data)
                        if unknownLibraryMatched:
                            #check whether this library is actually unknown, by comparing it with identified dicts
                            #unkLib = unknownLibraryMatched.group(1).lower().decode()
                            unkVer = unknownLibraryMatched.group(2).decode()
                            unkjsFile = ((os.path.basename(jsFile)).replace(
                                '.js', '')).replace('.min', '')

                            if (not self.isLibExistInList(
                                    unkjsFile, unkVer,
                                    self.identifiedKnLibrariesList)):
                                #put this unknown library in the unknown dictionary. use the filename instead - safer
                                self.identifiedUnLibrariesList.append({
                                    'lib': unkjsFile,
                                    'ver': unkVer,
                                    'detectMethod': self.DetectionType.
                                                    FILENAME_FILECONTENT.name,
                                    'jsFilename': os.path.basename(jsFile),
                                    'path': jsFile
                                })
                            isApplication = False
                            break
                            #do not need to check the rest of the unknown regexes

            #if none of the above regexes match, then it is likely an application
            if isApplication:
                self.identifiedApplicationsList.append(jsFile)

        return (self.identifiedKnLibrariesList, self.identifiedUnLibrariesList,
                self.identifiedApplicationsList)

    def isLibExistInList(self, lib, ver, listOfDict):
        for item in listOfDict:
            if (item['lib'].lower() == lib.lower() and
                    item['ver'].lower() == ver.lower()):
                return True
        return False

    def showIdentifiedLibraries(self):
        for identified in self.identifiedKnLibrariesList:
            print("Identified Known Lib: {}".format(identified))

        print()
        for identified in self.identifiedUnLibrariesList:
            print("Identified UnKnown Lib: {}".format(identified))

        print()
        for app in self.identifiedApplicationsList:
            print("Likely_Application: {}".format(app))
