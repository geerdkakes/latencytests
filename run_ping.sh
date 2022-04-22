#!/usr/bin/env bash

#############################################
# Script to run an nuttcp session on a remote host
#  Variables:
#   -s <session id>
#   -M <MTU size>
#   -s_ip server IP to which the nuttcp client will connect
#   -d_ip device IP at which the device can be reached (preferably a fixed connection)
#   -t time in seconds to run the trial
#   -d up | down (up: traffic generated by device, down: traffic generated by server)
#   -d_user <userid> from device
#############################################

#############################################
# default variables
#############################################
source variables.sh
size=64
time=10
testdate="$(date +"%m-%d-%y_%H.%M")"
session_id="$(date +"%s")"
scriptname=$0
#############################################
# interpret command line flags
#############################################
while [ -n "$1" ]
do
    case "$1" in
        -s) session_id="$2"
            echo "${scriptname}: session id: $session_id"
            shift ;;
        -size) size="$2"
            echo "${scriptname}: size used: ${size}"
            shift ;;
        -s_ip) serverIP="$2"
            echo "${scriptname}: Server IP to contact: ${serverIP}"
            shift ;;
        -d_ip) deviceIP="$2"
            echo "${scriptname}: Device IP to contact: ${deviceIP}"
            shift ;;
        -t) time="$2"
            echo "${scriptname}: Time in seconds to test: ${time}"
            shift ;;
        -d_user) userid_device="$2"
            echo "${scriptname}: userid used at device: ${userid_device}"
            shift ;;
        -interval) interval_msec="$2"
            echo "${scriptname}: interval in msec used: ${interval_msec}"
            shift ;;
        -test_id) testID="$2"
            echo "${scriptname}: testID set to: ${testID}"
            shift ;;
        --) shift
            break ;;
        *) echo "${scriptname}: $1 is not an option";;
    esac
    shift
done

#############################################
# set dynamic variables
#############################################
interval_sec=$(echo "${interval_msec}/1000" | node -p)
count=$(echo "Math.round(1000*${time}/${interval_msec})" | node -p)

###########################################
# create data directories with session id
###########################################
mkdir -p ${data_dir_server}/${session_id}
ssh ${userid_device}@${deviceIP} "/usr/bin/mkdir -p ${data_dir_device}/${session_id}"

######################################################################
# ping test with the following parameters:
#  -D                   : print timestamp
#  -i <interval>        : insterval in seconds
#  -c <count>           : number of packets to send
#  -l                   : preload 
#  -n                   : no name lookup
#  -s                   : packet size
#  <ip address>
######################################################################
echo "${scriptname}: running ping on client side with count: ${count} and interval_sec: ${interval_sec}"
echo "${scriptname}: ssh ${userid_device}@${deviceIP} \"sudo ping -D -i ${interval_sec} -n -c ${count} -s ${size} -l 5 ${serverIP} > ${data_dir_device}/${session_id}/device_ping_${testdate}.log\""
ssh ${userid_device}@${deviceIP} "echo size:${size} > ${data_dir_device}/${session_id}/device${testID}_ping_${testdate}.log"
ssh ${userid_device}@${deviceIP} "echo intervalmsec:${interval_msec} >> ${data_dir_device}/${session_id}/device${testID}_ping_${testdate}.log"
ssh ${userid_device}@${deviceIP} "echo title:${session_id} >> ${data_dir_device}/${session_id}/device${testID}_ping_${testdate}.log"
ssh ${userid_device}@${deviceIP} "sudo ping -D -i ${interval_sec} -n -c ${count} -s ${size} -l 5 ${serverIP} >> ${data_dir_device}/${session_id}/device${testID}_ping_${testdate}.log"
if [ ${?} -eq 1 ]; then
    echo "${scriptname}:  ping with ${testID} closed with error"
else
    echo "${scriptname}:  Finished ping test on ${testID}"
fi
sleep 3


##########################################
# retrieve device logfile 
##########################################
scp ${userid_device}@${deviceIP}:${data_dir_device}/${session_id}/device_nuttcp_${testdate}.log  ${data_dir_server}/${session_id}/
echo "${scriptname}: stored nuttcp output at ${data_dir_server}/${session_id}/device${testID}_ping_${testdate}.log"
