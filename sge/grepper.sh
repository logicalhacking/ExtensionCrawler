#!/usr/bin/bash
set -o nounset

PATTERN=$1
HOST=${2:-sharc.shef.ac.uk}
BASEDIR=$( cd $(dirname "$0"); cd ..; pwd -P )
TARGETDIR='/data/$USER/grepper-'$(date +%Y%m%d-%H%M%S)

echo "Creating dirs ..."
ssh "$HOST" mkdir -p $TARGETDIR/ExtensionCrawler
ssh "$HOST" mkdir -p $TARGETDIR/logs
ssh "$HOST" mkdir -p $TARGETDIR/out

echo "Pushing $BASEDIR to $HOST:$TARGETDIR/ExtensionCrawler ..."
rsync -zr "$BASEDIR/" $HOST:"$TARGETDIR/ExtensionCrawler"

echo "Starting job ..."
ssh "$HOST" qsub \
  -v BASEDIR="$TARGETDIR",PATTERN="$PATTERN" \
  -t 1-256 \
  -j yes \
  -o "$TARGETDIR/logs" \
  "$TARGETDIR/ExtensionCrawler/sge/grepper.sge"
