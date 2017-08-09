#!/bin/bash
# m h  dom mon dow   command
# 01 02 * * * (cd ~/ExtensionCrawler; ((git fetch ; git checkout production; git pull) &> /dev/null))
# 07 02 * * * ~/ExtensionCrawler/scripts/global_update.sh


export LD_LIBRARY_PATH=$HOME/local/lib:/usr/local/lib:$LD_LIBRARY_PATH
export PATH=$HOME/local/bin:/usr/local/bin:$PATH

ARCHIVE=${1:-/srv/Shared/BrowserExtensions/}
CRAWLERHOME=${2:-~/ExtensionCrawler}
LOGPREFIX=$ARCHIVE/log/`date --iso-8601=ns`
LOG=$LOGPREFIX-global.log 

date +'* Start Updating Extensions Archive (%c)' | tee $LOG

SQLITE=`which sqlite3`

# Update extensions
(cd $CRAWLERHOME; (./crawler -d -a $ARCHIVE > $LOGPREFIX.log))


date +'* Update Finished (%c)' | tee -a $LOG

