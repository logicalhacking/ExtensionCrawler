#!/bin/bash
# m h  dom mon dow   command
# 15 01 * * * (cd ~/ExtensionCrawler; ((git fetch ; git checkout production; git pull) &> /dev/null))
# 07 02 * * * ~/ExtensionCrawler/scripts/global_update.sh

ARCHIVE=${1:-/srv/Shared/BrowserExtensions/archive}
CRAWLERHOME=${2:-~/ExtensionCrawler}
LOGPREFIX=$ARCHIVE/log/`date --iso-8601=ns`
LOG=$LOGPREFIX-global.log 

date +'* Start Updating Extensions Archive (%c)' | tee $LOG

# Update extensions
(cd $CRAWLERHOME; (./crawler -p 32 -d -a $ARCHIVE > $LOGPREFIX.log))

date +'* Update Finished (%c)' | tee -a $LOG

ERRORS=`$LOGPREFIX.log | sort -k 5,5 -u | wc -l`
EXTENSIONS=`grep "Updating db" $LOGPREFIX.log | wc -l`
echo "ERROR LOG: $ERRORS (out of $EXTENSIONS)"
echo "=========="
grep ERROR $LOGPREFIX.log | sort -k 5,5 -u | sort -k 3,3 

