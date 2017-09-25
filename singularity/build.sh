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

IMAGE=ExtensionCrawler

if [ -f ${IMAGE}.img ]; then 
    echo "Image ${IMAGE}.img exists already."
    echo "Please remove/rename the image and restart this script"
    exit 1
else
    singularity create --size 600 ${IMAGE}.img
    sudo singularity bootstrap ${IMAGE}.img ${IMAGE}.def
fi
