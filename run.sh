#!/bin/bash
# Move straight to the project directory path context 
cd "$(dirname "$0")"

# The LD_PRELOAD prefix bridges the modern rpicam lens stream into your virtual python framework
LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libv4l2.so DISPLAY=:0 /home/campi/env/bin/python3 main.py