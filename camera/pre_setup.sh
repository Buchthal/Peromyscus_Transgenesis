#!/usr/bin/bash
set -e

source /home/pi/.profile

# base
sudo apt-get update
sudo apt install -y screen

sudo bash -c "sed -i 's/CONF_SWAPSIZE=100/CONF_SWAPSIZE=2048/g' /etc/dphys-swapfile"
sudo reboot
