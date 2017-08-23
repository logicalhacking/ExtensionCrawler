#!/usr/bin/bash
set -o nounset

PATTERN=$1
HOST=${2:-sharc.shef.ac.uk}
BASEDIR=$( cd $(dirname "$0"); cd ..; pwd -P )/
TARGETDIR='/data/$USER/grepper-'$(date +%Y%m%d-%H%M%S)

SGEFILE="$BASEDIR/sge/grepper.sge"

echo "Creating $HOST:$TARGETDIR/ExtensionCrawler ..."
ssh "$HOST" mkdir -p $TARGETDIR/ExtensionCrawler

echo "Pushing $BASEDIR to $HOST:$TARGETDIR/ExtensionCrawler ..."
rsync -zr "$BASEDIR" $HOST:"$TARGETDIR/ExtensionCrawler"

echo "Pushing $SGEFILE to $HOST:$TARGETDIR/grepper.sge ..."
rsync -zr "$SGEFILE" $HOST:"$TARGETDIR/grepper.sge"

echo "Starting job ..."
ssh "$HOST" qsub \
  -v BASEDIR="$TARGETDIR",PATTERN="$PATTERN" \
  -t 1-256 \
  -j yes \
  -o "$TARGETDIR" \
  "$TARGETDIR/grepper.sge"
