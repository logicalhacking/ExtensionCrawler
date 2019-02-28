#!/usr/bin/bash
set -o errexit
set -o nounset

if [ "$#" -lt 2 ]; then
  echo "Usage: $0 <IMGFILE> <DEFFILE>"
  exit 1
fi

IMGFILE=$(realpath $1)
IMGDIR=$(dirname "$IMGFILE")
DEFFILE=$(realpath $2)
DEFDIR=$(dirname "$DEFFILE")

if [ -f "$IMGFILE" ]; then
  rm "$IMGFILE"
fi

docker build --tag=singularitybuilder-arch -f singularitybuilder-arch.Dockerfile .
docker run -v "$IMGDIR:$IMGDIR" -v "$DEFDIR:$DEFDIR" --privileged singularitybuilder-arch:latest singularity build "$IMGFILE" "$DEFFILE"
