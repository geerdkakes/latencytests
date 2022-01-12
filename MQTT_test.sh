#!/usr/bin/env bash

#############################################
# fixed variables
#############################################
source variables.sh
testdate="$(date +"%m-%d-%y_%H.%M")"
scriptname=$0
#############################################
# default variables
#############################################
bytes="100"
interval="30"
duration="900"
session_id="$(date +"%s")"

#############################################
# interpret command line flags
#############################################
while [ -n "$1" ]
do
    case "$1" in
        -b) bytes="$2"
            echo "${scriptname}: size payload to test with: $bytes bytes"
            shift ;;
        -t) duration="$2"
            echo "${scriptname}: duration to test with: $duration seconds"
            shift ;;
        -i) interval="$2"
            echo "${scriptname}: interval to test with: $interval mili seconds"
            shift ;;
        -s) session_id="$2"
            echo "${scriptname}: session id: $session_id"
            shift ;;
        -s_ip) serverIP="$2"
            echo "${scriptname}: Server IP to contact: ${serverIP}"
            shift ;;
        -d_ip) deviceIP="$2"
            echo "${scriptname}: Device IP to contact: ${deviceIP}"
            shift ;;
        -d_user) userid_device="$2"
            echo "${scriptname}: userid used at device: ${userid_device}"
            shift ;;
        --) shift
            break ;;
        *) echo "$1 is not an option";;
    esac
    shift
done

###########################################
# create data directories with session id
###########################################
mkdir -p ${data_dir_server}/${session_id}
ssh ${userid_device}@${deviceIP} "/usr/bin/mkdir -p ${data_dir_device}/${session_id}"

##########################################
# start device site proces
##########################################
echo "${scriptname}: run mqtt test on device with interval of ${interval} and pakage size of ${bytes}Bytes."
ssh ${userid_device}@${deviceIP} "/usr/bin/node ${mqtt_delay_app} -h mqtt://${serverIP} \
                                                                       -b ${bytes} \
                                                                       -i ${interval} \
                                                                       -d ${duration} \
                                                                       -v 1 \
                                                                       -u testuser01 \
                                                                       -s 'sdf29239sdjf24' \
                                                                       -o ${data_dir_device}/${session_id}/device_mqtt_test_data_${testdate}.log \
                                                                       > ${data_dir_device}/${session_id}/device_mqtt_test_verbose_${testdate}.log"

sleep 1

##########################################
# retrieve device logfile 
##########################################
scp ${userid_device}@${deviceIP}:${data_dir_device}/${session_id}/device_mqtt_test_data_${testdate}.log  ${data_dir_server}/${session_id}/
scp ${userid_device}@${deviceIP}:${data_dir_device}/${session_id}/device_mqtt_test_verbose_${testdate}.log  ${data_dir_server}/${session_id}/

