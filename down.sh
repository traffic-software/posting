#!/bin/bash
sudo apt-get install supervisor -y

# Get files from Google Drive

# $1 = file ID
# $2 = file name
# FILEID="1dT8oGJZNQt5crDYtuywoHEPGIeSiq7_6"
# URL="https://docs.google.com/uc?export=download&id=$FILEID"

# wget --load-cookies /tmp/cookies.txt "https://docs.google.com/uc?export=download&confirm=$(wget --quiet --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate $URL -O- | sed -rn 's/.*confirm=([0-9A-Za-z_]+).*/\1\n/p')&id=$FILEID" -O pkey.tar && rm -rf /tmp/cookies.txt
# docker load -i pkey.tar