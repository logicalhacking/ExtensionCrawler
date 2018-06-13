#!/bin/bash
set -o nounset
set -o errexit

REMOTE_ARCHIVE=/shared/brucker_research1/Shared/BrowserExtensions/archive
REMOTE_TARGET_DIR_PREFIX=/data/\$USER
NUM_THREADS=48
SGE_EXTRA_ARGS='-P rse -m a -l rmem=8G -M "msherzberg1@sheffield.ac.uk" -j yes'
PY_EXTRA_ARGS=''

usage() {
  echo "Usage:"
  echo "  -a <path> (archive path, default: ${REMOTE_ARCHIVE})"
  echo "  -t <path> (target directory, default: ${REMOTE_TARGET_DIR_PREFIX})"
  echo "  -m <num_threads> (degree of parallelism, default: ${NUM_THREADS})"
  echo "  -s \"<args>\" (qsub arguments, default: ${SGE_EXTRA_ARGS})"
  echo "  -p \"<args>\" (python script arguments, default: ${PY_EXTRA_ARGS})"
}

while getopts ":a:t:s:p:m:" o; do
  case "${o}" in
    a)
      REMOTE_ARCHIVE=${OPTARG}
      ;;
    t)
      REMOTE_TARGET_DIR_PREFIX=${OPTARG}
      ;;
    m)
      NUM_THREADS=${OPTARG}
      ;;
    s)
      SGE_EXTRA_ARGS+=" ${OPTARG}"
      ;;
    p)
      PY_EXTRA_ARGS+=" ${OPTARG}"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
done

shift $((OPTIND-1))

BASEDIR=$( cd $(dirname "$0"); cd ..; pwd -P )
TEMP_FOLDER=$(mktemp -d)
TARGETDIR="${REMOTE_TARGET_DIR_PREFIX}/create-db-$(date +%Y%m%d-%H%M%S)"

echo "Using target dir: $TARGETDIR"
ssh sharc.shef.ac.uk mkdir -p $TARGETDIR/logs

echo "Pushing sge script ..."
scp "$BASEDIR/sge/create-db.sge" sharc.shef.ac.uk:"$TARGETDIR/create-db.sge"

echo "Building image..."
if [ -f "$BASEDIR/singularity/create-db.img" ]; then
  rm -f "$BASEDIR/singularity/create-db.img"
fi
sudo singularity build "$BASEDIR/singularity/create-db.img" "$BASEDIR/singularity/ExtensionCrawler-dev.def"

echo "Pushing image..."
scp "$BASEDIR/singularity/create-db.img" sharc.shef.ac.uk:"$TARGETDIR/create-db.img"


echo "Gathering extension IDs..."
ssh sharc.shef.ac.uk find "${REMOTE_ARCHIVE}/data" -name "*.tar" | grep -Po "[a-p]{32}" > ${TEMP_FOLDER}/extension.ids

NO_IDS=$(cat ${TEMP_FOLDER}/extension.ids | wc -l)

echo "Found $NO_IDS IDs!"
if [ "$NO_IDS" = 0 ]; then
  echo "Nothing to do!"
  exit 0
fi

echo "Pushing extension IDs..."
scp ${TEMP_FOLDER}/extension.ids sharc.shef.ac.uk:$TARGETDIR/

NO_BATCH_JOBS=$(((NO_IDS+1)/75000+1))
JOBS_PER_BATCH=$((NO_IDS/NO_BATCH_JOBS+1))

for run_no in $(seq 1 $NO_BATCH_JOBS); do
  FIRST_ID=$(((run_no-1) * $JOBS_PER_BATCH + 1))
  LAST_ID=$((run_no * $JOBS_PER_BATCH))

  echo "Starting job $run_no ..."
  (set -x; ssh sharc.shef.ac.uk qsub \
    -tc $((NUM_THREADS/NO_BATCH_JOBS)) \
    -t ${FIRST_ID}-${LAST_ID} \
    -wd "$TARGETDIR" \
    -o "$TARGETDIR/logs" \
    ${SGE_EXTRA_ARGS} \
    "$TARGETDIR/create-db.sge" -a "$REMOTE_ARCHIVE" -e "${TARGETDIR}/extension.ids" -N $NO_IDS ${PY_EXTRA_ARGS})
done
