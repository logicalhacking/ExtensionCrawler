#!/bin/bash
# m h  dom mon dow   command
# 07 02 * * * ~/ExtensionCrawler/scripts/global_update.sh

ARCHIVE=${1:-/srv/Shared/BrowserExtensions/}
CRAWLERHOME=${2:-~/ExtensionCrawler}



# Update git repro
(cd $CRAWLERHOME; ((git fetch ; git checkout production; git pull) &> /dev/null))

# Update extensions
(cd $CRAWLERHOME; (./crawler -d -a $ARCHIVE > $ARCHIVE/log/`date --iso-8601=ns`.log))

# Update small database
#rm -f $ARCHIVE/db/aa-ac.sqlite
(cd $CRAWLERHOME; (./scripts/generate_small_db.sh $ARCHIVE/data $ARCHIVE/db/aa-ac.sqlite > $ARCHIVE/log/`date --iso-8601=ns`-sqlite-aa-ac.log))

# Update full database
rm -f $ARCHIVE/db/full.sqlite
(FIRSTDB=$(find "$ARCHIVE"/data/aa* -name "*.sqlite" | head -n 1);
 sqlite3 "$FIRSTDB" .schema | sqlite3 "$ARCHIVE"/db/full.sqlite;
 echo "Used $FIRSTDB for schema";
 find "$ARCHIVE"/data/ -name "*.sqlite" -exec "$CRAWLERHOME/scripts/merge_dbs.sh" "{}" "$ARCHIVE"/db/full.sqlite \; ;
) > $ARCHIVE/log/`date --iso-8601=ns`-sqlite-full.log
if [ -f "$ARCHIVE"/db/full.sqlite ]; then 
  bzip2 "$ARCHIVE"/db/full.sqlite 
fi
