#!/usr/bin/env bash
set -e

#link local files to /usr/local
echo "1"
rm -rf /usr/local/aquamonitor
mkdir /usr/local/aquamonitor
cp -r app/. /usr/local/aquamonitor

#setup service and start
cp aquamonitor.service /etc/systemd/system
systemctl enable aquamonitor
systemctl start aquamonitor