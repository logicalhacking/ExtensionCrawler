#!/bin/bash

KILL="NO"
ARCHIVE="/srv/Shared/BrowserExtensions/archive"

while [[ $# -gt 0 ]]
do
key="$1"
case $key in
    -a|--ARCHIVE)
    ARCHIVE="$2"
    shift # past argument
    shift # past value
    ;;
    --kill)
    KILL=YES
    shift # past argument
    ;;
    *)    # unknown option
    shift # past argument
    ;;
esac
done

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
    if [[ "$KILL" == "YES" ]];then
        echo "  KILL mode enabled, killing running global_update.sh instances"
        echo "       (executing pkill -9 -P $PIDS)"
        pkill -9 -P $PIDS 
        pkill -f "ExtensionCrawler//crawler "
    fi
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

DATE=`date --utc +%Y-%m-%d`
TIME=`date --utc +%H:%M:%S`

EXTS=`grep 'Updating .* extensions' $LATESTLOG  \
 | head -1 \
 | sed -e 's/^.*---//' \
       -e 's/Updating/\\"/' \
       -e 's/extensions (/\\";\\"/' \
       -e 's/including forums)/\\"/' \
       -e 's/ //g'`

if [[ "$EXTS" == "" ]]; then
    EXTS=";"
fi

LASTPDOWNLOADS=`tail -1 $ARCHIVE/monitor/updates.csv | cut -d'"' -f12`
LASTSDOWNLOADS=`tail -1 $ARCHIVE/monitor/updates.csv | cut -d'"' -f14`
LASTMAIL=`tail -1 $ARCHIVE/monitor/updates.csv | cut -d'"' -f18`

if [[ "$NUM" == "0" ]]; then
MAIL=0
else
   if [[ "$LASTPDOWNLOADS$LASTSDOWNLOADS" == "$PDOWNLOADS$SDOWNLOADS" ]]; then 
       if [[ "$LASTMAIL" == "0" ]]; then 
           echo "" | mail $USER -s "Extension Download Stalled!";
       fi;
       MAIL=1;
   else
       MAIL=0;
   fi
fi

MEM=`free | tail -2 | awk '{print $2 " " $3 " " $4}' | xargs | sed -e 's/ /\";\"/g'`

echo "\"$DATE $TIME\";\"$NUM\";\"$PIDS\";$EXTS;\"$PDOWNLOADS\";\"$SDOWNLOADS\";\"$ERRORS\";\"$MAIL\";\"$MEM\"" >> $ARCHIVE/monitor/updates.csv
gnuplot -e "monitordir='$ARCHIVE/monitor'" $BASEDIR/download-report-one-week.gp

