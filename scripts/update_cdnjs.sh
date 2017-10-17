#!/bin/bash

LOGPREFIX=$ARCHIVE/log/`date --iso-8601=ns`
LOG=$LOGPREFIX-cdnjs.log 

SING_IMG=/shared/brucker_research1/Shared/BrowserExtensions/archive/filedb/ExtensionCrawler-cdnjs.img
cp $SING_IMG $(SING_IMG).bak
SING_EXEC="singularity exec -w --pwd /opt/ExtensionCrawler -B $TMPDIR:/tmp $SING_IMG"
ls "$SING_IMG" > /dev/null

# Update production branch of WebCrawler repository
$SING_EXEC git fetch > $LOGPREFIX.log
$SING_EXEC git checkout production >> $LOGPREFIX.log
$SING_EXEC git pull >> $LOGPREFIX.log

# Update cdnjs git repository and update cdnjs data base table
$SING_EXEC ./cdnjs-git-miner -v -p 1 -u -a /opt/archive >> $LOGPREFIX.log

