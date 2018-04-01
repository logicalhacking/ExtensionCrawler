#!/bin/bash
ARCHIVE=${1:-/srv/Shared/BrowserExtensions/archive}
CRAWLERHOME=${2:-~/ExtensionCrawler}
IMAGE=${3:-/shared/brucker_research1/Shared/BrowserExtensions/bin/ExtensionCrawler.img}
LATESTLOG=`ls $ARCHIVE/log/*0.log | tail -n 1`
LATESTGLOBALLOG=`ls $ARCHIVE/log/*-global.log | tail -n 1`
BASEDIR=$(dirname "$0")


PIDS=""
echo "# Checking update status"
if ps u -C global_update.sh > /dev/null; then 
    NUM=`ps u -C global_update.sh | tail -n +2 | wc -l`
    echo "* $NUM instances of global_update.sh still running (WARNING)"
    PIDS=`ps u -C global_update.sh | tail -n +2  | awk '{print $2}' | xargs`
    echo "  Running PIDs: $PIDS"
else
    echo "* global_update.sh not running"
    NUM=0
fi

echo "* current status"
PDOWNLOADS=`grep 'Updating extension $' $LATESTLOG | wc -l`
echo "  * parallel downloads finished:   $PDOWNLOADS" 
SDOWNLOADS=`grep 'Updating extension  (' $LATESTLOG | wc -l`
echo "  * sequential downloads finished: $SDOWNLOADS" 
echo "  * Updating info from log ($LATESTLOG):"
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

DATE=`date +%Y-%m-%d`
TIME=`date +%H:%M:%S`

EXTS=`grep 'Updating .* extensions' $LATESTLOG  \
 | head -1 \
 | sed -e 's/^.*---//' \
 | sed -e 's/Updating/\\"/' \
 | sed -e 's/extensions (/\\";\\"/' \
 | sed -e 's/including forums)/\\"/' \
 | sed -e 's/ //g'`

if [[ "$EXTS" == "" ]]; then
    EXTS=";"
fi

LASTPDOWNLOADS=`tail -1 $ARCHIVE/monitor/updates.csv | cut -d'"' -f14`
LASTSDOWNLOADS=`tail -1 $ARCHIVE/monitor/updates.csv | cut -d'"' -f16`
LASTMAIL=`tail -1 $ARCHIVE/monitor/updates.csv | cut -d'"' -f20`

if [[ "$NUM" == "0" ]]; then
MAIL=0
else
   if [[ "$LASTPDOWNLOADS$LASTSDOWNLOADS" == "$PDOWNLOADS$SDOWNLOADS" ]]; then 
       if [[ "$LASTMAIL" == "0" ]]; then 
           echo "" | mail $USER -s echo "Extension Download Stalled!";
       fi;
       MAIL=1;
   else
       MAIL=0;
   fi
fi

echo "\"$DATE $TIME\";\"$NUM\";\"$PIDS\";$EXTS;\"$PDOWNLOADS\";\"$SDOWNLOADS\";\"$ERRORS\";\"$MAIL\"" >> $ARCHIVE/monitor/updates.csv
gnuplot -e "monitordir='$ARCHIVE/monitor'" $BASEDIR/download-report-one-week.gp

