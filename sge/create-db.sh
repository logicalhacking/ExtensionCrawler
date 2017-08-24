#!/usr/bin/bash
set -o nounset
set -o errexit

ARCHIVE=${1:-$(ssh sharc.shef.ac.uk find /shared/brucker_research1/Shared/BrowserExtensions/.snapshot -maxdepth 1 -name \"D*\" | sort -r | head -n1)}
TARGETBASEDIR=${2:-'/data/$USER'}

echo "Using archive $ARCHIVE"

TARGETDIR="${TARGETBASEDIR}/create-db-$(date +%Y%m%d-%H%M%S)"
BASEDIR=$( cd $(dirname "$0"); cd ..; pwd -P )

echo "Creating dirs ..."
ssh sharc.shef.ac.uk mkdir -p $TARGETDIR/ExtensionCrawler
ssh sharc.shef.ac.uk mkdir -p $TARGETDIR/logs
ssh sharc.shef.ac.uk mkdir -p $TARGETDIR/out

echo "Pushing $BASEDIR to sharc.shef.ac.uk:$TARGETDIR/ExtensionCrawler ..."
rsync -zr "$BASEDIR/" sharc.shef.ac.uk:"$TARGETDIR/ExtensionCrawler"

echo "Starting job ..."
ssh sharc.shef.ac.uk \
  ARCHIVE=\"$ARCHIVE\" \
  BASEDIR=\"$TARGETDIR\" \
  qsub \
  -V \
  -t 1-256 \
  -j yes \
  -o "$TARGETDIR/logs" \
  "$TARGETDIR/ExtensionCrawler/sge/create-db.sge"
