#!/bin/bash

source /home/pi/.profile

sec_interval=$1
sec_length=$2

time_interval=$(($sec_interval * 1000))
time_length=$(($sec_length * 1000))
sleep_time=300

function log {
    msg=$1
    timestamp=`date -Is`
    echo "[${timestamp}] $msg" >> /home/pi/image_capture_timelapse_log.txt
}



while true
do
    log "Starting timelapse for $time_length with interval $time_interval"

    raspistill -o /home/pi/stills/%10d.jpg -t $time_length --timelapse $time_interval --timestamp --height 480 --width 640 --nopreview  >> /home/pi/image_capture_timelapse_log.txt 2>&1

    log "Finished timelapse, starting processing"

    python /home/pi/image_processing.py -v >> /home/pi/image_processing_log.txt 2>&1

    log "Finished processing"
done
