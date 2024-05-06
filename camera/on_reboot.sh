date >> /home/pi/reboots.txt

source /home/pi/.profile

aws s3 cp s3://xxx/rpi/scripts/wpa_supplicant.conf /home/pi/wpa_supplicant.conf
sudo chown root:root /home/pi/wpa_supplicant.conf
sudo mv /home/pi/wpa_supplicant.conf /boot/wpa_supplicant.conf

# expected to fail if the file doesn't exist
sudo mv /boot/rpi_id /home/pi/rpi_id
sudo chown pi:pi /home/pi/rpi_id
