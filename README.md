# aquariummonitor

## requirements
- putty
- powershell

## pi setup
- `sudo apt-get update && sudo apt-get upgrade`
- install ssh server (see notes below)
- open powershell to the root directory and run `.\setup_transfer.ps1`

## debugging
to view the logs in real time, log into the server and run `tail -f /var/log/aquamonitor.log`


### notes
#### ssh server install
- `sudo apt-get install openssh-server`
- `sudo raspi-config` -> 'interfacing options' -> 'ssh' -> enable service