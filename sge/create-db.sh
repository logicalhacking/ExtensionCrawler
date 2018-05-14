#!/usr/bin/bash
set -o nounset
set -o errexit

BASEDIR=$( cd $(dirname "$0"); cd ..; pwd -P )

NRJOBS=${NRJOBS:-256}
echo "Using $NRJOBS jobs"

JOBRANGE=${JOBRANGE:-1-$NRJOBS}
echo "Executing jobs $JOBRANGE"

ARCHIVE=${ARCHIVE:-$(ssh sharc.shef.ac.uk find /shared/brucker_research1/Shared/BrowserExtensions/archive/.snapshot -maxdepth 1 -name \"D*\" | sort -r | head -n1)}
echo "Using archive: $ARCHIVE"

TARGETDIR="${TARGETDIR:-/data/\$USER}/create-db-$(date +%Y%m%d-%H%M%S)"
echo "Using target dir: $TARGETDIR"

SING_IMG_SRC="${SING_IMG_SRC:-/shared/brucker_research1/Shared/BrowserExtensions/excrawl.img}"
SING_IMG="$TARGETDIR/excrawl.img"
if ! ssh sharc.shef.ac.uk [ -f "$SING_IMG_SRC" ]; then
  echo -n "$SING_IMG_SRC does not exist! Generate new image and push? (yes/abort): "
  read confirm
  if [ "$confirm" != yes ]; then
    exit 0
  fi
  echo "Creating new image ..."
  (cd "$BASEDIR/singularity"; ./build.sh -f)
  echo "Pushing new image ..."
  scp "$BASEDIR/singularity/ExtensionCrawler.img" sharc.shef.ac.uk:"$SING_IMG_SRC"
fi
echo "Creating dirs ..."
ssh sharc.shef.ac.uk mkdir -p $TARGETDIR/logs

echo "Copying $SING_IMG_SRC to $SING_IMG"
ssh sharc.shef.ac.uk cp "$SING_IMG_SRC" "$SING_IMG"

echo "Pushing sge script ..."
scp "$BASEDIR/sge/create-db.sge" sharc.shef.ac.uk:"$TARGETDIR/create-db.sge"

if ! [ -z "${EXTIDLISTFILE:-}" ]; then
  echo "Pushing list with extension ids ..."
  scp "$EXTIDLISTFILE" sharc.shef.ac.uk:"$TARGETDIR/ids"
fi

echo "Starting job ..."
ssh sharc.shef.ac.uk \
  SING_IMG=\"$SING_IMG\" \
  ARCHIVE=\"$ARCHIVE\" \
  BASEDIR=\"$TARGETDIR\" \
  MAX_SGE_TASK_ID=\"$NRJOBS\" \
  qsub \
  -V \
  -m a \
  -l rmem=8G \
  -M "msherzberg1@sheffield.ac.uk" \
  -t $JOBRANGE \
  -j yes \
  -o "$TARGETDIR/logs" \
  "$TARGETDIR/create-db.sge" \
  $*
