#!/usr/bin/env bash
set -e

#link local files to /usr/local
rm -rf /usr/local/aquamonitor
mkdir /usr/local/aquamonitor
cp -r app/. /usr/local/aquamonitor

#setup service and start
cp aquamonitor.service /etc/systemd/system
cp fertilizer.service /etc/systemd/system
cp fertilizer.timer /etc/systemd/system
sudo systemctl enable aquamonitor fertilizer fertilizer.timer
sudo systemctl stop aquamonitor fertilizer fertilizer.timer
sudo systemctl start aquamonitor fertilizer.timer