#!/bin/bash
# m h  dom mon dow   command
# 07 02 * * * ~/ExtensionCrawler/scripts/global_update.sh

ARCHIVE=${1:-/srv/Shared/BrowserExtensions/}
CRAWLERHOME=${2:-~/ExtensionCrawler}
LOGPREFIX=$ARCHIVE/log/`date --iso-8601=ns`
date +'* Start Updating Code Repository (%c)'

# Update git repro
(cd $CRAWLERHOME; ((git fetch ; git checkout production; git pull) &> /dev/null))

date +'* Start Updating Extensions Archive (%c)'

# Update extensions
(cd $CRAWLERHOME; (./crawler -d -a $ARCHIVE > $LOGPREFIX.log))

date +'* Start Creating aa-ac.sqlite Data Base (%c)'
# Update small database
rm -f $ARCHIVE/db/aa-ac.sqlite
(cd $CRAWLERHOME; (./scripts/generate_small_db.sh $ARCHIVE/data $ARCHIVE/db/aa-ac.sqlite &> $LOGPREFIX-sqlite-aa-ac.log))
if [ $? -ne "0" ]; then 
  echo "    Creation of aa-ac.sqlite failed - see log file for details"
else 
  SIZE=`du -k $ARCHIVE/db/aa-ac.sqlite | cut -f1`
  echo "    Created aa-ac.sqlite successfully ($SIZE kb)"
fi

if [ -f "$ARCHIVE"/db/aa-ac.sqlite ]; then 
  date +'* Start Compressing aa-ac.sqlite Data Base (%c)'
  rm -f $ARCHIVE/db/aa-ac.sqlite.bz2
  pbzip2 -f "$ARCHIVE"/db/aa-ac.sqlite 
  if [ $? -ne "0" ]; then 
    echo "    Creation of aa-ac.sqlite.bz2 failed"
  else 
    SIZE=`du -k $ARCHIVE/db/aa-ac.sqlite.bz2 | cut -f1`
    echo "    Created aa-ac.sqlite.bz2 successfully ($SIZE kb)"
  fi
fi

date +'* Start Creating full.sqlite Data Base (%c)'
# Update full database
rm -f $ARCHIVE/db/full.sqlite
(FIRSTDB=$(find "$ARCHIVE"/data/aa* -name "*.sqlite" | head -n 1);
 sqlite3 "$FIRSTDB" .schema | sqlite3 "$ARCHIVE"/db/full.sqlite;
 echo "Used $FIRSTDB for schema";
 find "$ARCHIVE"/data/ -name "*.sqlite" -exec "$CRAWLERHOME/scripts/merge_dbs.sh" "{}" "$ARCHIVE"/db/full.sqlite \; ;
) &> $LOGPREFIX-sqlite-full.log
if [ $? -ne "0" ]; then 
  echo "    Creation of full.sqlite failed - see log file for details"
else 
  SIZE=`du -k $ARCHIVE/db/full.sqlite | cut -f1`
  echo "    Created full.sqlite successfully ($SIZE kb)"
fi

if [ -f "$ARCHIVE"/db/full.sqlite ]; then 
  date +'* Start Compressing full.sqlite Data Base (%c)'
  rm -f $ARCHIVE/db/full.sqlite.bz2
  pbzip2 -f "$ARCHIVE"/db/full.sqlite 
  if [ $? -ne "0" ]; then 
    echo "    Creation of full.sqlite.bz2 failed"
  else 
    SIZE=`du -k $ARCHIVE/db/full.sqlite.bz2 | cut -f1`
    echo "    Created full.sqlite.bz2 successfully ($SIZE kb)"
  fi
fi

# date +'* Start Compressing Log files (%c)'
# for f in $ARCHIVE/log/*.log; do 
#   pbzip2 -f $f &> /dev/null 
# done 

date +'* Update Finished (%c)'

