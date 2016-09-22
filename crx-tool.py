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

import argparse
import binascii
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA

from Crypto.Signature import PKCS1_v1_5

class CrxFile:
    def __init__(self,filename,magic,version,pk_len,sig_len,pk,sig,header_len,data): 
        self.file       = filename
        self.magic      = magic
        self.version    = version
        self.pk_len     = pk_len
        self.sig_len    = sig_len
        self.pk         = pk
        self.sig        = sig
        self.header_len = header_len
        self.data       = data
        
def is_valid_magic(magic):
    return (b'Cr24' == magic)

def is_crxfile (filename):
    "Check magic number: crx files should start with \"Cr24\"."
    file      = open (filename, 'rb')
    magic     = file.read(4)
    file.close()
    return is_valid_magic(magic)

def check_signature(pk,sig,data):
    key  = RSA.importKey(pk)
    hash = SHA.new(data)
    return PKCS1_v1_5.new(key).verify(hash, sig)
 
def read_crx(filename):
    "Read header of an crx file (https://developer.chrome.com/extensions/crx)."
    file       = open (filename, 'rb')
    magic      = file.read(4)
    version    = int.from_bytes(file.read(4), byteorder='little')
    pk_len     = int.from_bytes(file.read(4), byteorder='little')
    sig_len    = int.from_bytes(file.read(4), byteorder='little')
    pk         = file.read(pk_len)
    sig        = file.read(sig_len)
    header_len = 16+pk_len+sig_len
    data       = file.read()
    file.close()
    return CrxFile(filename,magic,version,pk_len,sig_len,pk,sig,header_len,data)

def print_crx_info(verbose,crx):
    if is_valid_magic(crx.magic):
        magic="valid"
    else:
        magic="invalid"
    if check_signature(crx.pk,crx.sig,crx.data):
        sig="valid"
    else:
        sig="invalid"
    print("Filename:    "+crx.file)
    print("Header size: "+str(crx.header_len))
    print("Size:        "+str(crx.header_len+len(crx.data)))
    print("Magic byte:  "+str(crx.magic.decode("utf-8"))+" ("+magic+")")
    print("Version:     "+str(crx.version))
    print("Signature:   "+sig)
    print("Public Key ["+str(crx.pk_len)+"]:")
    key  = RSA.importKey(crx.pk)
    print (key.exportKey().decode("utf-8"))
    if verbose:
        print("Signature ["+str(crx.sig_len)+"]: "+str(binascii.hexlify(crx.sig)))
    
def verify_crxfile (verbose, filename):
    if is_crxfile(filename):
        if verbose:
            print("Found correct magic bytes.")
        print_crx_info(verbose,read_crx(filename))
        return 0    
    else:
        if verbose:
            print("No valid magic bytes found")
        return -1
            
def extract_crxfile(verbose, force, filename):
    print("Not yet implemented: extract crxfile(",verbose,", ", force,", ", filename, ")")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="chrome extension archive (*.crx)")
    parser.add_argument("-c", "--check", help="verify format and signature of <file>",
                        action="store_true")
    parser.add_argument("-e", "--extract", help="extract <file>",
                        action="store_true")
    parser.add_argument("-f", "--force", help="apply action also to (potential) invalid files",
                        action="store_true")
    parser.add_argument("-v", "--verbose", help="increase verbosity",
                        action="store_true")
    args = parser.parse_args()
    
    if args.extract:
        retval = extract_crxfile(args.verbose, args.force, args.file)
    else: 
        retval = verify_crxfile(args.verbose, args.file)

    exit(retval)    
    
if __name__ == "__main__":
    main()

