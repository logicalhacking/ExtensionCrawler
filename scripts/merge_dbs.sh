#!/bin/bash
FROM_DB=$1
TO_DB=$2

if [ -z $FROM_DB ] || ! [ -f $FROM_DB ]; then
  echo "source db not provided or does not exist"
  exit 1
fi

if [ -z $TO_DB ] || ! [ -f $TO_DB ]; then
  echo "destination db not provided or does not exist"
  exit 1
fi

echo "Merging $FROM_DB into $TO_DB..."

sqlite3 $FROM_DB .dump | grep -v "^CREATE TABLE" | sqlite3 $TO_DB
