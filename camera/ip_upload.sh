source /home/pi/.profile
hn=`hostname -I`
rpi_id=`cat /home/pi/rpi_id | xargs`
echo $hn | aws s3 cp - s3://xxx/rpi/$rpi_id/ip_address
echo `date -Is`
