#!/usr/bin/env bash

function get_external_time {
    ext_time_raw=`cat </dev/tcp/time.nist.gov/13 | grep -Po "\d{2}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}"`
    ext_time_conv=`date -d "${ext_time_raw}" +'%F %T'`
    echo $ext_time_conv
}

function force_sync_time {
    currenttime=`date +'%F %T'`
    ext_time_str=$(get_external_time)
    sudo date -s "${ext_time_str}"
    log "set time (${currenttime}) to external (${ext_time_str})"
}

function log {
    msg=$1
    timestamp=`date -Is`
    echo "[${timestamp}] $msg" >> /home/pi/restart_services_log.txt
}

function log_capture {
    msg=$1
    timestamp=`date -Is`
    echo "[${timestamp}] $msg" >> /home/pi/image_capture_timelapse_log.txt
}

function log_ip_upload {
    msg=$1
    timestamp=`date -Is`
    echo "[${timestamp}] $msg" >> /home/pi/cronlog.txt
}

function log_processing {
    msg=$1
    timestamp=`date -Is`
    echo "{'message': '$msg','time': '${timestamp}'}" >> /home/pi/image_processing_log.json
}

function delete_logs {
    sudo rm /var/log/kern.log /var/log/kern.log.1 /var/log/syslog /var/log/syslog.1
}

function do_reboot {
    sleep 1
    sudo reboot
    exit 0
}

disk_size=`df --output=pcent / | tr -dc '0-9'`
if (( $disk_size > 90 )); then
    delete_logs
    log "deleted logs because disk is at ${disk_size}"
    do_reboot
fi


# don't continue if just rebooted in last 10 minutes
uptimedate=$(uptime --since)
twenty_min_ago=`date +'%F %T' -d "-20 minutes"`
if [[ $twenty_min_ago < $uptimedate ]]; then
    exit 0
fi

# force sync time if greater or less than 2 minutes from external time
# ext_time_str=$(get_external_time)
# two_min_ago=`date +'%F %T' -d "-2 minutes"`
# two_min_from_now=`date +'%F %T' -d "+2 minutes"`
# if [[ $ext_time_str < $two_min_ago ]] || [[ $ext_time_str > $two_min_from_now ]]; then
#     currenttime=`date +'%F %T'`
#     log "resetting time because ${ext_time_str} is out of sync with ${currenttime}"
#     force_sync_time
# fi


# reset time if ip_upload hasn't happened in last 2 minutes
ip_log_date=`date -r cronlog.txt +'%F%T%z'`
four_min_ago=`date +'%F%T%z' -d "-4 minutes"`
if [[ $ip_log_date < $four_min_ago ]]; then
    log "resetting time because cronlog hasn't been updated since ${ip_log_date}"
    force_sync_time
fi


# reset time if there is an upload error
logline=`tail -n 1 /home/pi/cronlog.txt`
if [[ $logline =~ "failed" ]] || [[ $logline =~ "error" ]]; then
    log "resetting time because of an ip_upload error: ${logline}"
    force_sync_time
fi


# don't continue if still starting up capture or if just restarted
last_image_date=`ls stills | tail -n 1 | grep -Po "\d{10}" | xargs -I{} date -d @{} +'%F %T'`
ten_min_ago=`date +'%F %T' -d "-10 minutes"`
if [[ $ten_min_ago < $last_image_date ]]; then
    exit 0
fi


# don't continue if nighttime, plus buffer
currenttime=$(date +%H:%M)
if [[ "$currenttime" < "08:20" ]]; then
    exit 0
fi


# reboot if nothing 5x in a row
nothing_count=`tail -n 2 /home/pi/image_processing_log.json | grep -o -E -i "(nothing to process|restarting|error)" | wc -l`
if (( $nothing_count >= 2 )); then
    log "rebooting because nothing count for image processing is at least 2"

    log_processing 'rebooting: nothing count'

    do_reboot
fi


# reboot if ip upload failing
failure_count=`tail -n 2 /home/pi/cronlog.txt | grep -o -E -i "(fail|error)" | wc -l`
if (( $failure_count >= 2 )); then
    log "rebooting because failure count for ip upload is at least 2"

    log_ip_upload "rebooting: failure count"

    do_reboot
fi


# restart image capture if image processing has nothing to process or there is an error
logline=`tail -n 1 /home/pi/image_processing_log.json`
if [[ $logline =~ "nothing to process" ]] || [[ $logline =~ "Error" ]]; then
    log "restarting image_capture_timelapse service because image_processing_log has an error: ${logline}"
    log_capture "restarting log error"
    log_processing "restarting log error"

    sudo systemctl stop image_capture_timelapse.service
    sudo systemctl start image_capture_timelapse.service
fi


last_image_date=`ls stills | tail -n 1 | grep -Po "\d{10}" | xargs -I{} date -d @{} +'%F %T'`
image_processing_log_date=`date -r image_processing_log.json +'%F %T'`
twenty_min_ago=`date +'%F %T' -d "-20 minutes"`
if [[ $twenty_min_ago > $last_image_date ]] || [[ $twenty_min_ago > $image_processing_log_date ]]; then
    log "restarting image_capture_timelapse service because image_capture and image_processing log date: $last_image_date, $image_processing_log_date"
    log_capture "restarting date"
    log_processing "restarting date"

    sudo systemctl stop image_capture_timelapse.service
    sudo systemctl start image_capture_timelapse.service
fi
