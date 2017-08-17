#!/bin/bash
# m h  dom mon dow   command
# 15 01 * * * (cd ~/ExtensionCrawler; ((git fetch ; git checkout production; git pull) &> /dev/null))
# 33 01 * * * ~/ExtensionCrawler/scripts/global_update_db.sh
# 07 02 * * * ~/ExtensionCrawler/scripts/global_update.sh


export LD_LIBRARY_PATH=$HOME/local/lib:/usr/local/lib:$LD_LIBRARY_PATH
export PATH=$HOME/local/bin:/usr/local/bin:$PATH

ARCHIVE=${1:-/srv/Shared/BrowserExtensions/}
CRAWLERHOME=${2:-~/ExtensionCrawler}
LOGPREFIX=$ARCHIVE/log/`date --iso-8601=ns`
LOG=$LOGPREFIX-global-db.log 

DBARCHIVE=`find $ARCHIVE/.snapshot -maxdepth 1 -mindepth 1 -name "D*" | head -n 1`

SQLITE=`which sqlite3`

date +"* Start Creating aa-ac.build.sqlite Data Base (%c) using $SQLITE (data: $DBARCHIVE/data)" | tee -a $LOG
# Update small database
rm -f $ARCHIVE/db/aa-ac.build.*

(cd $CRAWLERHOME; (./scripts/generate_small_db.sh $DBARCHIVE/data $ARCHIVE/db/aa-ac.build.sqlite &> $LOGPREFIX-sqlite-aa-ac.log))
if [ $? -ne "0" ]; then 
  echo "    Creation of aa-ac.build.sqlite failed - see log file for details" | tee -a $LOG
else 
  SIZE=`du -k $ARCHIVE/db/aa-ac.build.sqlite | cut -f1`
  echo "    Created aa-ac.build.sqlite successfully ($SIZE kb)" | tee -a $LOG
fi

if [ -f "$ARCHIVE"/db/aa-ac.build.sqlite ]; then 
  date +'* Start Compressing aa-ac.sqlite Data Base (%c)' | tee -a $LOG
  pbzip2 -f "$ARCHIVE"/db/aa-ac.build.sqlite 
  if [ $? -ne "0" ]; then 
      echo "    Creation of aa-ac.sqlite.build.bz2 failed"  | tee -a $LOG
      rm -f $ARCHIVE/db/aa-ac.build.*
  else      
      rm -f $ARCHIVE/db/aa-ac.sqlite.bz2
      mv $ARCHIVE/db/aa-ac.build.sqlite.bz2 $ARCHIVE/db/aa-ac.sqlite.bz2
      SIZE=`du -k $ARCHIVE/db/aa-ac.sqlite.bz2 | cut -f1`
      echo "    Created aa-ac.sqlite.bz2 successfully ($SIZE kb)" | tee -a $LOG
  fi
fi

date +"* Start Creating full.sqlite Data Base (%c) using $SQLITE (data: $DBARCHIVE/data)" | tee -a $LOG
# Update full database
rm -f $ARCHIVE/db/full.build.*
"$CRAWLERHOME/scripts/merge_dbs" "$DBARCHIVE/data" "$ARCHIVE/db/full.build.sqlite" &> $LOGPREFIX-sqlite-full.log
if [ $? -ne "0" ]; then 
  echo "    Creation of full.build.sqlite failed - see log file for details" | tee -a $LOG
else 
  SIZE=`du -k $ARCHIVE/db/full.build.sqlite | cut -f1`
  echo "    Created full.build.sqlite successfully ($SIZE kb)" | tee -a $LOG
fi

if [ -f "$ARCHIVE"/db/full.build.sqlite ]; then 
  rm -f "$ARCHIVE"/db/full.sqlite
  cp  "$ARCHIVE"/db/full.build.sqlite "$ARCHIVE"/db/full.sqlite
  date +'* Start analysis (%c)' | tee -a $LOG
  queries=`dirname $0`
  result=`sqlite3 "$ARCHIVE"/db/full.sqlite < $queries/../queries/get_added_permissions.sql`
  echo $result > $LOGPREFIX-analysis.log
  echo $result | mail root -s "Extension Analysis" 
  date +'*       Analysis finished (%c)' | tee -a $LOG
  
  date +'* Start Compressing full.build.sqlite Data Base (%c)' | tee -a $LOG
  pbzip2 -f "$ARCHIVE"/db/full.build.sqlite 
  if [ $? -ne "0" ]; then 
      rm -f $ARCHIVE/db/full.build.*
      echo "    Creation of full.sqlite.bz2 failed" | tee -a $LOG
  else 
      rm -f $ARCHIVE/db/full.sqlite.bz2
      mv $ARCHIVE/db/full.build.sqlite.bz2 $ARCHIVE/db/full.sqlite.bz2
      SIZE=`du -k $ARCHIVE/db/full.sqlite.bz2 | cut -f1`
      echo "    Created full.sqlite.bz2 successfully ($SIZE kb)" | tee -a $LOG
  fi
fi

# date +'* Start Compressing Log files (%c)'
# for f in $ARCHIVE/log/*.log; do 
#   pbzip2 -f $f &> /dev/null 
# done 

date +'* Update Finished (%c)' | tee -a $LOG

