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
        -d_ip_modem_prefix) prefixmodemIP="$2"
            echo "${scriptname}: modem prefix ip: ${prefixmodemIP}"
            shift ;;
        -d_user) userid_device="$2"
            echo "${scriptname}: userid used at device: ${userid_device}"
            shift ;;
        -test_id) test_id="$2"
            echo "${scriptname}: test_id used at device: ${test_id}"
            shift ;;
        -udp_uplink_port) udp_uplink_port="$2"
            echo "${scriptname}: udp_uplink_port used at device: ${udp_uplink_port}"
            shift ;;
        -udp_downlink_port) udp_downlink_port="$2"
            echo "${scriptname}: udp_downlink_port used at server: ${udp_downlink_port}"
            shift ;;
        --) shift
            break ;;
        *) echo "$1 is not an option";;
    esac
    shift
done

if [ -z ${prefixmodemIP+x} ]; then
    # ports not set
    prefixmodemIP=""
    echo "${scriptname}: prefixmodemIP not found, please specify using option \"-d_ip_modem_prefix\". Needed to find the IP address to send udp packets to."
else
    readarray -td, prefixmodemIP_arr <<<"$prefixmodemIP,"; 
    unset 'prefixmodemIP_arr[-1]'
fi

###########################################
# find device ip address
###########################################
for prefixmodemIP in "${prefixmodemIP_arr[@]}"; do
    echo "${scriptname}: trying to find device IP with prefix: ${prefixmodemIP} for device ${test_id}"
    deviceipaddress=$(ssh ${userid_device}@${deviceIP} /usr/sbin/ifconfig | grep "inet ${prefixmodemIP}"  | awk '{print $2}'
    if [ ! "${device_modem_ipaddress}" = "" ]; then
        echo "${scriptname}: device ip found for device ${test_id}: ${device_modem_ipaddress}"
        break
    fi
done

###########################################
# create data directories with session id
###########################################
mkdir -p ${data_dir_server}/${session_id}
ssh ${userid_device}@${deviceIP} "/usr/bin/mkdir -p ${data_dir_device}/${session_id}"

##########################################
# start server receving side proces
##########################################
echo "${scriptname}: listening for udp packets on server at port ${udp_uplink_port} for packets from ${test_id}."
/usr/bin/node ${udp_app_receive} -t ${duration} -p ${udp_uplink_port} -r false > ${data_dir_server}/${session_id}/server_received_${test_id}_UDP_echo_${testdate}.log  &

##########################################
# start device site sending proces
##########################################
echo "${scriptname}: run udp uplink test on device to server port ${udp_uplink_port} with interval of ${interval} and pakage size of ${bytes}Bytes from dev ${test_id}."
ssh ${userid_device}@${deviceIP} "/usr/bin/node ${udp_app_send}        -h ${serverIP} \
                                                                       -c up_${test_id} \
                                                                       -p ${udp_uplink_port} \
                                                                       -s ${bytes} \
                                                                       -i ${interval} \
                                                                       -j true \
                                                                       -t ${duration} \
                                                                            > ${data_dir_device}/${session_id}/device_send_${test_id}_UDP_echo_${testdate}.log" &


##########################################
# start device site receiving proces
##########################################
echo "${scriptname}: listening for udp packets on device at port ${udp_downlink_port} for packets from ${test_id}."
ssh ${userid_device}@${deviceIP} "/usr/bin/node ${udp_app_receive} -t ${duration} -p ${udp_downlink_port} -r false > ${data_dir_device}/${session_id}/device_received_${test_id}_UDP_echo_${testdate}.log"  &


##########################################
# start server  side sending proces
##########################################
echo "${scriptname}: run udp downlink test on server to device port ${udp_downlink_port} with interval of ${interval} and pakage size of ${bytes} Bytes to dev ${test_id} with IP ${device_modem_ipaddress}."
/usr/bin/node ${udp_app_send}                                          -h ${device_modem_ipaddress} \
                                                                       -c down_${test_id} \
                                                                       -p ${udp_downlink_port} \
                                                                       -s ${bytes} \
                                                                       -i ${interval} \
                                                                       -j true \
                                                                       -t ${duration} \
                                                                            > ${data_dir_server}/${session_id}/server_send_${test_id}_UDP_echo_${testdate}.log



##########################################
# retrieve device logfile 
##########################################
sleep 4
echo "${scriptname}: retrieving log: scp ${userid_device}@${deviceIP}:${data_dir_device}/${session_id}/device_send_${test_id}_UDP_echo_${testdate}.log  ${data_dir_server}/${session_id}/"
scp ${userid_device}@${deviceIP}:${data_dir_device}/${session_id}/device_send_${test_id}_UDP_echo_${testdate}.log  ${data_dir_server}/${session_id}/
echo "${scriptname}: retrieving log: scp ${userid_device}@${deviceIP}:${data_dir_device}/${session_id}/device_received_${test_id}_UDP_echo_${testdate}.log  ${data_dir_server}/${session_id}/"
scp ${userid_device}@${deviceIP}:${data_dir_device}/${session_id}/device_received_${test_id}_UDP_echo_${testdate}.log  ${data_dir_server}/${session_id}/
