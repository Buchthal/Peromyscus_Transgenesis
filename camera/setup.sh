#!/usr/bin/bash
set -ex

source /home/pi/.profile

# base
sudo apt-get update
sudo apt-get upgrade -y
sudo apt install -y python3-pip

sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.7 2
sudo update-alternatives --install /usr/bin/python python /usr/bin/python2.7 1

pip3 install opencv-python-headless
sudo apt install -y libatlas-base-dev libhdf5-dev libhdf5-serial-dev libatlas-base-dev libjasper-dev libqtgui4 libqt4-test python3-opencv
# pip3 install numpy --force

pip3 install sqlalchemy psycopg2==2.8.6 JSON-log-formatter==0.1.0 ujson boto3 ipdb


# aws setup
pip3 install awscli --upgrade --user
echo "export PATH=/home/pi/.local/bin:$PATH" >> /home/pi/.profile
export PATH=/home/pi/.local/bin:$PATH


# wireless check up
touch /home/pi/wireless_check_up_log.txt
aws s3 cp s3://xxx/rpi/scripts/wireless_check_up.sh /home/pi/wireless_check_up.sh
chmod +x wireless_check_up.sh


# set up image capture
mkdir -p /home/pi/stills
aws s3 cp s3://xxx/rpi/scripts/ip_upload_ready.sh /home/pi/ip_upload.sh
aws s3 cp s3://xxx/rpi/scripts/image_capture_timelapse.sh /home/pi/image_capture_timelapse.sh
aws s3 cp s3://xxx/rpi/scripts/image_capture_timelapse.service /home/pi/image_capture_timelapse.service
aws s3 cp s3://xxx/rpi/scripts/image_processing.py /home/pi/image_processing.py

touch /home/pi/restart_services_log.txt
aws s3 cp s3://xxx/rpi/scripts/restart_services_if_down.sh /home/pi/restart_services_if_down.sh

chmod +x /home/pi/ip_upload.sh
chmod +x /home/pi/image_capture_timelapse.sh

touch /home/pi/image_capture_timelapse_log.txt
sudo mv /home/pi/image_capture_timelapse.service /etc/systemd/system/image_capture_timelapse.service
sudo systemctl enable image_capture_timelapse.service
sudo systemctl start image_capture_timelapse.service


# cron
aws s3 cp s3://xxx/rpi/scripts/cron_jobs.txt /home/pi/cron_jobs.txt
crontab /home/pi/cron_jobs.txt


# logs
sudo journalctl --vacuum-size=100M


# set swap back to normal
sudo bash -c "sed -i 's/CONF_SWAPSIZE=2048/CONF_SWAPSIZE=100/g' /etc/dphys-swapfile"
sudo reboot
