#!/bin/bash
# m h  dom mon dow   command
# 15 01 * * * (cd ~/ExtensionCrawler; ((git fetch ; git checkout production; git pull) &> /dev/null))
# 07 02 * * * ~/ExtensionCrawler/scripts/global_update.sh

ARCHIVE=${1:-/srv/Shared/BrowserExtensions/archive}
CRAWLERHOME=${2:-~/ExtensionCrawler}
IMAGE=${3:-/shared/brucker_research1/Shared/BrowserExtensions/bin/ExtensionCrawler.img}
LOGPREFIX=$ARCHIVE/log/`date --utc --iso-8601=ns`
LOG=$LOGPREFIX-global.log 

date --utc +'* Start Updating Extensions Archive (%c)' | tee $LOG

# Update extensions
(singularity exec --bind /srv/:/srv/ $IMAGE crawler -p 42 -d --pystuck -a $ARCHIVE > $LOGPREFIX.log ) |& ts -m '%Y-%m-%dT%H:%M:%S' | tee $LOGPREFIX-stderr.log

date --utc +'* Update Finished (%c)' | tee -a $LOG


ERRORS=`grep ERROR $LOGPREFIX.log | sort -k 5,5 -u | wc -l`
EXTENSIONS=`grep "Updating db" $LOGPREFIX.log | wc -l`
echo "ERROR LOG: $ERRORS (out of $EXTENSIONS)"
echo "=========="
grep ERROR $LOGPREFIX.log | sort -k 5,5 -u | sort -k 3,3 

