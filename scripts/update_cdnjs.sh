#!/bin/bash

SING_IMG=/shared/brucker_research1/Shared/BrowserExtensions/archive/filedb/ExtensionCrawler-cdnjs.img
SING_EXEC="singularity exec -w --pwd /opt/ExtensionCrawler -B $TMPDIR:/tmp $SING_IMG"
ls "$SING_IMG" > /dev/null

# Update production branch of WebCrawler repository
$SING_EXEC git fetch
$SING_EXEC git checkout production
$SING_EXEC git pull

# Update cdnjs git repository and update cdnjs data base table
$SING_EXEC ./cdnjs-git-miner -v -p 1 -u -a /opt/archive

