#!/usr/bin/bash
set -o nounset
set -o errexit

PATTERN=$1
BASEDIR=$( cd $(dirname "$0"); cd ..; pwd -P )
TARGETDIR='/data/$USER/grepper-'$(date +%Y%m%d-%H%M%S)

echo "Creating dirs ..."
ssh sharc.shef.ac.uk mkdir -p $TARGETDIR/ExtensionCrawler
ssh sharc.shef.ac.uk mkdir -p $TARGETDIR/logs
ssh sharc.shef.ac.uk mkdir -p $TARGETDIR/out

echo "Pushing $BASEDIR to sharc.shef.ac.uk:$TARGETDIR/ExtensionCrawler ..."
rsync -zr "$BASEDIR/" sharc.shef.ac.uk:"$TARGETDIR/ExtensionCrawler"

echo "Starting job ..."
ssh sharc.shef.ac.uk \
  BASEDIR=\"$TARGETDIR\" \
  PATTERN=\"$PATTERN\" \
  qsub \
  -V \
  -t 1-256 \
  -j yes \
  -o "$TARGETDIR/logs" \
  "$TARGETDIR/ExtensionCrawler/sge/grepper.sge"
