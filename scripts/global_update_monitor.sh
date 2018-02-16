#!/bin/bash
ARCHIVE=${1:-/srv/Shared/BrowserExtensions/archive}
CRAWLERHOME=${2:-~/ExtensionCrawler}
IMAGE=${3:-/shared/brucker_research1/Shared/BrowserExtensions/bin/ExtensionCrawler.img}
LATESTLOG=`ls -t $ARCHIVE/log/*0.log | head -n 1`
LATESTGLOBALLOG=`ls -t $ARCHIVE/log/*-global.log | head -n 1`

echo "# Checking update status"
if ps u -C global_update.sh > /dev/null; then 
    NUM=`ps u -C global_update.sh | tail -n +2 | wc -l`
    echo "* $NUM instances of global_update.sh still running (WARNING)"
else
    echo "* global_update.sh not running"
fi

echo "* current status"
grep 'Updating .* extensions' $LATESTLOG  | sed -e 's/^.*---//'

echo ""
echo "## Latest log:"
cat $LATESTGLOBALLOG

ERRORS=`grep ERROR $LATESTLOG | sort -k 5,5 -u | wc -l`
EXTENSIONS=`grep "Updating db" $LATESTLOG | wc -l`
echo "## ERROR LOG: $ERRORS (out of $EXTENSIONS)"
grep ERROR $LATESTLOG | sort -k 5,5 -u | sort -k 3,3

echo "# Server utilization"
top b -n 1 | head -n 15
