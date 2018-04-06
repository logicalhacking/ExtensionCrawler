#!/bin/sh
# Copyright 2017,2018 The University of Sheffield, UK
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

BASE=ExtensionCrawler
BASESIZE=600
BINDIR=/srv/Shared/BrowserExtensions/bin

print_help()
{
    echo "Usage: $prog [OPTION] "
    echo ""
    echo "Build a singularity image (fat application) for all ExtensenCrawler utilities."
    echo ""
    echo "  --help, -h              display this help message"
    echo "  --force, -f             overwrite existing singularity image"
    echo "  --cdnjs, -c             include cdnjs repository (ca. 125 GB)"
    echo "  --install, -i           install image into $BINDIR"
}


FORCE="false"
CDNJS="false"
INSTALL="false"

while [ $# -gt 0 ]
do
    case "$1" in
        --force|-f)
            FORCE="true";;
        --cdnjs|-c)
            CDNJS="true";;
        --install|-i)
            INSTALL="true";;
        --help|-h)
            print_help
            exit 0;;
    esac
    shift
done



if [ "$CDNJS" = "true" ]; then
    IMAGE=${BASE}-cdnjs.img
    BASESIZE=$((BASESIZE+134400))
else
    IMAGE=${BASE}.img
fi


if [ -f ${IMAGE} ]; then 
    if [ "$FORCE" = "true" ]; then
        rm -f ${IMAGE}
    else
        echo "Image ${IMAGE} exists already."
        echo "Please remove/rename the image and restart this script"
        exit 1
    fi
fi

if [ "$CDNJS" = "true" ]; then
    echo "Creating writable $IMAGE ($BASESIZE MiB) using ${BASE}.def"
    # TODO: --writable for 'build' action is deprecated due to some sparse file
    # issues; it is recommended to use --sandbox; however, that creates a
    # folder, which is probable not what we want here...
    sudo singularity build --writable ${IMAGE} ${BASE}.def
    sudo singularity image.expand --size ${BASESIZE} --writable ${IMAGE} ${BASE}.def
else 
    echo "Creating read-only $IMAGE using ${BASE}.def"
    sudo singularity build ${IMAGE} ${BASE}.def
fi

if [ "$INSTALL" = "true" ]; then
    if [ -f $BINDIR/$IMAGE ]; then
        mv $BINDIR/$IMAGE $BINDIR/$IMAGE.bak
    fi
    mv $IMAGE $BINDIR
fi
