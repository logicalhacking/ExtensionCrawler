#!/bin/bash

# Usage:
# ./generate_small_db.sh [BASEDIR] [DBPATH] [EXTENSIONCRAWLER]
#   [BASEDIR]           path to extension data, needs to contain aaa, aab, etc (defaults to sharc path)
#   [DBPATH]            path to output db (defaults to ~/aa-ac.sqlite)
#   [EXTENSIONCRAWLER]  path to git repo (defaults to ~/ExtensionCrawler)

BASEDIR=${1:-/shared/brucker_research1/Shared/BrowserExtensions/data}
DBPATH=${2:-~/aa-ac.sqlite}
EXTENSIONCRAWLER=${3:-~/ExtensionCrawler}

find "$BASEDIR"/aa* -name "*.sqlite" -exec "$EXTENSIONCRAWLER/scripts/merge_dbs.sh" "{}" "$DBPATH" \;
find "$BASEDIR"/ab* -name "*.sqlite" -exec "$EXTENSIONCRAWLER/scripts/merge_dbs.sh" "{}" "$DBPATH" \;
find "$BASEDIR"/ac* -name "*.sqlite" -exec "$EXTENSIONCRAWLER/scripts/merge_dbs.sh" "{}" "$DBPATH" \;
