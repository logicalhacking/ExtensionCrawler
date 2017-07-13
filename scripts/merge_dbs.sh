#!/bin/bash
FROM_DB=$1
TO_DB=$2

if [ -z $FROM_DB ] || ! [ -f $FROM_DB ]; then
  echo "source db not provided or does not exist"
  exit 1
fi

if [ -z $TO_DB ]; then
  echo "destination db not provided"
  exit 1
fi

if ! [ -f $TO_DB ]; then
  echo "Creating $TO_DB ..."
  sqlite3 $FROM_DB .schema | grep -Eiv \
    -e "^CREATE TABLE IF NOT EXISTS (\"|')?[a-z]+_content(\"|')?\(" \
    -e "^CREATE TABLE IF NOT EXISTS (\"|')?[a-z]+_docsize(\"|')?\(" \
    -e "^CREATE TABLE IF NOT EXISTS (\"|')?[a-z]+_segments(\"|')?\(" \
    -e "^CREATE TABLE IF NOT EXISTS (\"|')?[a-z]+_stat(\"|')?\(" \
    -e "^CREATE TABLE IF NOT EXISTS (\"|')?[a-z]+_segdir(\"|')?\(" \
  | sqlite3 $TO_DB
fi

echo "Merging $FROM_DB into $TO_DB..."

sqlite3 $FROM_DB .dump | grep -Eiv \
  -e "^CREATE TABLE" \
  -e "^INSERT INTO (\"|')?sqlite_master(\"|')?" \
  -e "^INSERT INTO (\"|')?[a-z]+_segments(\"|')? " \
  -e "^INSERT INTO (\"|')?[a-z]+_segdir(\"|')? " \
  -e "^INSERT INTO (\"|')?[a-z]+_docsize(\"|')? " \
  -e "^INSERT INTO (\"|')?[a-z]+_stat(\"|')? " \
| sed -r "s/^INSERT INTO ([a-z]+)_content VALUES\([[:digit:]]+,/INSERT INTO \1 VALUES(/I" \
| sqlite3 $TO_DB
