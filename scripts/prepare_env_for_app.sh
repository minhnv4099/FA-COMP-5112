#!/bin/bash


pip install bpy==3.6.0 --extra-index-url https://download.blender.org/pypi/

# Export XDG_RUNTIME_DIR
echo "export XDG_RUNTIME_DIR=/tmp/runtime/gvfs/" >> ~/.bashrc

mkdir -p /tmp/runtime/gvfs/
source ~/.bashrc

# Install libEGL
apt update
apt install -y libegl1 libgl1 libopengl0 libxrandr2 libxinerama1 libxcursor1 libxi6

export RUNLEVEL=3
