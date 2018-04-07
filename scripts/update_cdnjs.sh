#!/bin/bash

ARCHIVE=${1:-/srv/Shared/BrowserExtensions/archive}
TMPDIR=${TMPDIR:-/tmp}
LOGPREFIX=$ARCHIVE/log/`date --utc --iso-8601=ns`
LOG=$LOGPREFIX-cdnjs.log 

SING_IMG=/shared/brucker_research1/Shared/BrowserExtensions/archive/filedb/ExtensionCrawler-cdnjs.img
date --utc +'* Create backup of disk image (%c)' | tee -a $LOG
cp $SING_IMG $SING_IMG.bak
SING_EXEC="singularity exec -w --pwd /opt/ExtensionCrawler -B $TMPDIR:/tmp $SING_IMG"
ls "$SING_IMG" > /dev/null

# Update production branch of WebCrawler repository
date --utc +'* Updating WebCrawler repository (%c)' | tee -a $LOG
$SING_EXEC git fetch >> $LOG
$SING_EXEC git checkout production >> $LOG 2>&1
$SING_EXEC git pull >> $LOG 2>&1
# $SING_EXEC pip3 install --system -e ../ExtensionCrawler

# Update cdnjs git repository and update cdnjs data base table
date --utc +'* Updating CDNJS  repository (%c)' | tee -a $LOG
$SING_EXEC ./cdnjs-git-miner -v -u -a /opt/archive >> $LOG
date --utc +'* Successfully updated CDNJS  repository (%c)' | tee -a $LOG

