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
bytes="149"
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
            echo "${scriptname}: bytes to test with: $bytes"
            shift ;;
        -t) duration="$2"
            echo "${scriptname}: duration to test: $duration"
            shift ;;
        -i) interval="$2"
            echo "${scriptname}: interval to test with: $interval"
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
# start server side proces
##########################################
echo "${scriptname}: run udp echo test on server"
/usr/bin/node ${udp_echo_app_server} -t ${duration} > ${data_dir_server}/${session_id}/server_UDP_echo_${testdate}.log  &

##########################################
# start device site proces
##########################################
echo "${scriptname}: run udp echo test on device with interval of ${interval} and pakage size of ${bytes}Bytes."
ssh ${userid_device}@${deviceIP} "/usr/bin/node ${udp_echo_app_device} -h ${serverIP} \
                                                                       -c 5g_device \
                                                                       -p 21000 \
                                                                       -s ${bytes} \
                                                                       -i ${interval} \
                                                                       -t ${duration} \
                                                                            > ${data_dir_device}/${session_id}/device_UDP_echo_${testdate}.log"

sleep 1

##########################################
# retrieve device logfile 
##########################################
scp ${userid_device}@${deviceIP}:${data_dir_device}/${session_id}/device_UDP_echo_${testdate}.log  ${data_dir_server}/${session_id}/

