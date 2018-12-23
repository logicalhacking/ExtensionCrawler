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

vuln_md5s = set()

# for version, md5 in execute("select version, md5 from cdnjs where typ='NORMALIZED' and path like '%.js' and library='jquery'"):
#     if LooseVersion(version) < LooseVersion('1.6.3'):
#         vuln_md5s.add(md5)
for version, md5 in execute("select version, md5 from cdnjs where typ='NORMALIZED' and path like '%.js' and library='angular.js'"):
    if LooseVersion(version) < LooseVersion('1.6.9'):
        vuln_md5s.add(md5)
print(f"found {len(vuln_md5s)} MD5s")

hits = 0
still_vuln = 0
for extid, g in groupby(execute("select extid, crx_etag, date, md5 from extension_update_most_recent join crxfile using (crx_etag) where typ='NORMALIZED' order by extid, date, crx_etag"), lambda x: x[0]):
    ext_is_vuln = False
    for crx_etag, g in groupby(map(lambda x: x[1:], g), lambda x: x[0]):
        is_vuln = False
        for date, md5, in map(lambda x: x[1:], g):
            if md5 in vuln_md5s:
                is_vuln = True
                break

        if not is_vuln and ext_is_vuln:
            print(f"{extid} got fixed in {crx_etag} on {date}!")
            hits += 1
        ext_is_vuln = is_vuln
    if is_vuln and date > datetime.datetime(year=2018, month=11, day=14):
        print(f"{extid} in {crx_etag} is still vulnerable as of {date}")
        still_vuln += 1

print(f"# fixes: {hits}")
print(f"# still vulnerable: {still_vuln}")

