#!/bin/bash

LOG_PATH="/home/pi/wireless_check_up_log.txt"
now=`date -Is`

# Which Interface do you want to check
wlan='wlan0'
# Which address do you want to ping to see if you can connect
pingip='google.com'

# Perform the network check and reset if necessary
/bin/ping -c 2 -I $wlan $pingip > /dev/null 2> /dev/null
if [ $? -ge 1 ] ; then
    echo "$now Network is DOWN. Perform a reset" >> $LOG_PATH
    /sbin/ifdown $wlan
    sleep 5
    /sbin/ifup --force $wlan
else
    echo "$now Network is UP." >> $LOG_PATH
fi

# touch /home/pi/wireless_check_up_log.txt
# */2 * * * * /usr/bin/bash /home/pi/wireless_check_up.sh >> /home/pi/wireless_check_up_log.txt 2>&1