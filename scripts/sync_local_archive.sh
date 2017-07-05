#!/bin/bash
DEST=${1:-`pwd`/archive}
HOUR=`TZ="Europe/London" date +%H`
if [ 00 -eq $HOUR ]; then
    DATE=`TZ='Europe/London' date -d "yesterday 13:00" +"%Y-%m-%d"`
else
    DATE=`TZ='Europe/London' date +"%Y-%m-%d"`
fi
SOURCE="/shared/brucker_research1/.snapshot/Daily\\ \\@\\ 01\\:00."$DATE"_0100"
echo "Syncing from $SOURCE"

mkdir -p $DEST/log
mkdir -p $DEST/db
rsync -r sharc:"$SOURCE/Shared/BrowserExtensions/db/aa-ac.sqlite.bz2" $DEST/db
bunzip2 -f $DEST/db/aa-ac.sqlite.bz2

mkdir -p $DEST/conf
rsync -r sharc:"$SOURCE/Shared/BrowserExtensions/conf/forums.conf" $DEST/conf
mv $DEST/conf/forums.conf $DEST/conf/forums-full.conf
grep "^a[abc]" $DEST/conf/forums-full.conf >  $DEST/conf/forums-sqlite.conf
grep "^aa[a-c]" $DEST/conf/forums-sqlite.conf >  $DEST/conf/forums.conf

mkdir -p $DEST/data
rsync -r sharc:"$SOURCE/Shared/BrowserExtensions/data/aa[a-c]" $DEST/data
