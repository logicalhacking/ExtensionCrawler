#!/bin/sh
# Copyright 2017 The University of Sheffield, UK
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

print_help()
{
    echo "Usage: $prog [OPTION] "
    echo ""
    echo "Build a singularity image (fat application) for all ExtensenCrawler utilities."
    echo ""
    echo "  --help, -h              display this help message"
    echo "  --force, -f             overwrite existing singularity image"
    echo "  --cdnjs, -c             include cdnjs repository (ca. 125 GB)"
}


FORCE="false"
CDNJS="false"

while [ $# -gt 0 ]
do
    case "$1" in
        --force|-f)
            FORCE="true";;
        --cdnjs|-c)
            CDNJS="true";;
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

echo "Creating $IMAGE ($BASESIZE MiB) using ${BASE}.def"
singularity create --size ${BASESIZE} ${IMAGE}
sudo singularity bootstrap ${IMAGE} ${BASE}.def
