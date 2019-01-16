import MySQLdb
from MySQLdb import cursors
import os
from distutils.version import LooseVersion
from itertools import groupby, islice
import datetime
import pickle

def execute(q, args=None):
    cachepath = "mysqlcache.tmp"
    cache = {}
    if os.path.exists(cachepath):
        with open(cachepath, 'rb') as f:
            try:
                cache = pickle.load(f)
            except Exception as e:
                print(e)

    if q in cache:
        print("retrieving query results from cache...")
        for row in cache[q]:
            yield row
    else:
        print("query not in cache, contacting db ...")
        db = MySQLdb.connect(read_default_file=os.path.expanduser("~/.my.cnf"), cursorclass=cursors.SSCursor)
        cursor = db.cursor()
        cursor.execute(q, args)

        result = []
        for row in cursor:
            result += [row]
            yield row
        cache[q] = result
        with open(cachepath, 'wb') as f:
            pickle.dump(cache, f)
            print("cache saved")

vuln_md5s = {}

for version, md5 in execute("select version, md5 from cdnjs where typ='NORMALIZED' and path like '%.js' and library='angular.js' and (filename in ('angular.js', 'angular.min.js'))"):
    if version not in vuln_md5s:
        vuln_md5s[version] = set()
    vuln_md5s[version].add(md5)

sorted_vuln_md5s = []
for library_version in sorted(vuln_md5s.keys(), key=LooseVersion)[::-1]:
    sorted_vuln_md5s += [(library_version, vuln_md5s[library_version])]


def get_angular_version(md5):
    for library_version, md5s in sorted_vuln_md5s:
        if md5 in md5s:
            return library_version

for extid, g in groupby(execute("select extid, crx_etag, date, md5 from extension_update_most_recent join crxfile using (crx_etag) where typ='NORMALIZED' order by extid, date, crx_etag"), lambda x: x[0]):
    result = {}

    for crx_etag, g in groupby(map(lambda x: x[1:], g), lambda x: x[0]):
        result_version = None
        for date, md5, in map(lambda x: x[1:], g):
            version = get_angular_version(md5)
            if version is not None and (result_version is None or LooseVersion(version) > LooseVersion(result_version)):
                result_version = version
        result[date] = result_version

    if len(set(result.values())) > 1:
        for date in sorted(result.keys()):
            print(f"{extid}|{date}|{result[date]}")
