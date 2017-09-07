#!/usr/bin/bash
set -o nounset
set -o errexit

NRJOBS=${NRJOBS:-256}
echo "Using $NRJOBS jobs"

ARCHIVE=${ARCHIVE:-$(ssh sharc.shef.ac.uk find /shared/brucker_research1/Shared/BrowserExtensions/.snapshot -maxdepth 1 -name \"D*\" | sort -r | head -n1)}
echo "Using archive: $ARCHIVE"

TARGETDIR="${TARGETDIR:-/data/\$USER}/grepper-$(date +%Y%m%d-%H%M%S)"
echo "Using target dir: $TARGETDIR"
BASEDIR=$( cd $(dirname "$0"); cd ..; pwd -P )

echo "Creating dirs ..."
ssh sharc.shef.ac.uk mkdir -p $TARGETDIR/ExtensionCrawler
ssh sharc.shef.ac.uk mkdir -p $TARGETDIR/logs
ssh sharc.shef.ac.uk mkdir -p $TARGETDIR/out

echo "Pushing $BASEDIR to sharc.shef.ac.uk:$TARGETDIR/ExtensionCrawler ..."
rsync -zr --exclude "$BASEDIR/archive" "$BASEDIR/" sharc.shef.ac.uk:"$TARGETDIR/ExtensionCrawler"

echo "Starting job ..."
ssh sharc.shef.ac.uk \
  ARCHIVE=\"$ARCHIVE\" \
  BASEDIR=\"$TARGETDIR\" \
  MAX_SGE_TASK_ID=\"$NRJOBS\" \
  qsub \
  -V \
  -t 1-$NRJOBS \
  -j yes \
  -o "$TARGETDIR/logs" \
  "$TARGETDIR/ExtensionCrawler/sge/grepper.sge" \
  $*
