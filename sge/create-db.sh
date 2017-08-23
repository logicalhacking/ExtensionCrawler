#!/usr/bin/bash
set -o nounset

HOST=${1:-sharc.shef.ac.uk}
BASEDIR=$( cd $(dirname "$0"); cd ..; pwd -P )
TARGETDIR='/data/$USER/create-db-'$(date +%Y%m%d-%H%M%S)

SGEFILE="$BASEDIR/sge/create-db.sge"

echo "Creating dirs ..."
ssh "$HOST" mkdir -p $TARGETDIR/ExtensionCrawler
ssh "$HOST" mkdir -p $TARGETDIR/logs
ssh "$HOST" mkdir -p $TARGETDIR/out

echo "Pushing $BASEDIR to $HOST:$TARGETDIR/ExtensionCrawler ..."
rsync -zr "$BASEDIR/" $HOST:"$TARGETDIR/ExtensionCrawler"

echo "Pushing $SGEFILE to $HOST:$TARGETDIR/create-db.sge ..."
rsync -zr "$SGEFILE" $HOST:"$TARGETDIR/create-db.sge"

echo "Starting job ..."
LAST_SNAPSHOT=$(ssh "$HOST" find /shared/brucker_research1/Shared/BrowserExtensions/.snapshot -maxdepth 1 -name \"D*\" | sort -r | head -n1)

ssh "$HOST" qsub \
  -v BASEDIR="$TARGETDIR",ARCHIVE=\'"$LAST_SNAPSHOT"\' \
  -t 1-256 \
  -j yes \
  -o "$TARGETDIR/logs" \
  "$TARGETDIR/create-db.sge"
