#!/usr/bin/env bash

#############################################
# (default) variables
#############################################
source variables.sh
testdate="$(date +"%m-%d-%y_%H.%M")"
scriptname=$0
duration="900"
session_id="$(date +"%s")"
protocols="tcp,udp"
snaplen=0
test_id="test_id"
#############################################
# interpret command line flags
#############################################
echo "${scriptname}: running record pcaps"

while [ -n "$1" ]
do
    case "$1" in
        -t) duration="$2"
            echo "${scriptname}: duration to test: $duration"
            shift ;;
        -s) session_id="$2"
            echo "${scriptname}: session id: $session_id"
            shift ;;
        -s_ip) serverIP="$2"
            echo "${scriptname}: Server IP to contact: ${serverIP}"
            shift ;;
        -s_if) serverIF="$2"
            echo "${scriptname}: Server IF to monitor: ${serverIF}"
            shift ;;
        -d_ip) deviceIP="$2"
            echo "${scriptname}: Device IP to contact: ${deviceIP}"
            shift ;;
        -d_user) userid_device="$2"
            echo "${scriptname}: userid used at device: ${userid_device}"
            shift ;;
        -d_ip_modem_prefix) prefixmodemIP="$2"
            echo "${scriptname}: modem prefix ip: ${prefixmodemIP}"
            shift ;;
        -ports) ports="$2"
            echo "${scriptname}: ports: ${ports}"
            shift ;;
        -protocols) protocols="$2"
            echo "${scriptname}: protocols: ${protocols}"
            shift ;;
        -snaplen) snaplen="$2"
            echo "${scriptname}: snaplen: ${snaplen}"
            shift ;;
        -test_id) test_id="$2"
            echo "${scriptname}: test_id: ${test_id}"
            shift ;;
        -extra_probe_enabled) extra_probe_enabled="$2"
            echo "${scriptname}: extra probe enabled found: ${extra_probe_enabled}"
            shift ;;
        -extra_probe_name) extra_probe_name="$2"
            echo "${scriptname}: extra probe name found: ${extra_probe_name}"
            shift ;;
        -extra_probe_dev) extra_probe_dev="$2"
            echo "${scriptname}: extra probe device found: ${extra_probe_dev}"
            shift ;;
        -extra_probe_snaplen) extra_probe_snaplen="$2"
            echo "${scriptname}: extra probe snaplen found: ${extra_probe_snaplen}"
            shift ;;
        --) shift
            break ;;
        *) echo "$1 is not an option";;
    esac
    shift
done

###########################################
# dynamic variables
###########################################
if [ -z ${ports+x} ]; then
    # ports not set
    ports=""
else
    readarray -td, ports_arr <<<"$ports,"; 
    unset 'ports_arr[-1]'
    ports="port ${ports_arr[0]}"

    for port in "${ports_arr[@]:1}"; do
        ports="${ports} or ${port}"
    done
fi
if [ -z ${prefixmodemIP+x} ]; then
    # ports not set
    prefixmodemIP=""
else
    readarray -td, prefixmodemIP_arr <<<"$prefixmodemIP,"; 
    unset 'prefixmodemIP_arr[-1]'
fi
readarray -td, protocols_arr <<<"$protocols,"; 
unset 'protocols_arr[-1]'
protocols="${protocols_arr[0]}"
for protocol in "${protocols_arr[@]:1}"; do
    protocols="${protocols} or ${protocol}"
done
###########################################
# create data directories with session id
###########################################
mkdir -p ${data_dir_server}/${session_id}
ssh ${userid_device}@${deviceIP} "/usr/bin/mkdir -p ${data_dir_device}/${session_id}/pcaps"


###########################################
# finding interface on device
###########################################
for prefixmodemIP in "${prefixmodemIP_arr[@]}"; do
    echo "${scriptname}: trying to find device interface using IP prefix: ${prefixmodemIP} for device ${test_id}"
    deviceinterface=$(ssh ${userid_device}@${deviceIP} /usr/sbin/ifconfig | grep "${prefixmodemIP}" -B 1 | head -1 | sed 's/\(.*\)\:\s\(.*\)/\1/')
    if [ ! "${deviceinterface}" = "" ]; then
        break
    fi
done
if [ "${deviceinterface}" = "" ]; then
  echo "${scriptname}: no ethernet device found to monitor. exiting"
  exit 1
else
  echo "${scriptname}: found device interface ${deviceinterface} for device ${test_id}"
fi
###########################################
# starting pcap logging on server and device
###########################################
echo "${scriptname}: logging on sever interface ${serverinterface}"
sudo tcpdump -n -i ${serverIF} ${protocols}  ${ports} -s ${snaplen} -B 4096 -G ${duration} -W 1 -w ${data_dir_server}/${session_id}/server_${test_id}_%Y-%m-%d_%H.%M.%S.pcap &
echo sudo tcpdump -n -i ${serverIF} ${protocols}  ${ports} -s ${snaplen} -B 4096 -G ${duration} -W 1 -w ${data_dir_server}/${session_id}/server_${test_id}_%Y-%m-%d_%H.%M.%S.pcap
if [ "${extra_probe_enabled^^}" = "TRUE" ]; then
    sudo tcpdump -n -i ${extra_probe_dev} udp  port 2152 -s ${extra_probe_snaplen} -B 4096 -G ${duration} -W 1 -w ${data_dir_server}/${session_id}/${extra_probe_name}_${test_id}_%Y-%m-%d_%H.%M.%S.pcap &
    echo sudo tcpdump -n -i ${extra_probe_dev} udp  port 2152 -s ${extra_probe_snaplen} -B 4096 -G ${duration} -W 1 -w ${data_dir_server}/${session_id}/${extra_probe_name}_${test_id}_%Y-%m-%d_%H.%M.%S.pcap
fi
echo "${scriptname}: logging device pcap on interface ${deviceinterface}"
echo ssh ${userid_device}@${deviceIP} sudo tcpdump -n -i ${deviceinterface} ${protocols}  ${ports} -s ${snaplen} -G ${duration} -W 1 -w ${data_dir_device}/${session_id}/pcaps/device_${test_id}_%Y-%m-%d_%H.%M.%S.pcap
ssh ${userid_device}@${deviceIP} sudo tcpdump -n -i ${deviceinterface} ${protocols}  ${ports} -s ${snaplen} -G ${duration} -W 1 -w ${data_dir_device}/${session_id}/pcaps/device_${test_id}_%Y-%m-%d_%H.%M.%S.pcap

sleep 5


###########################################
# retrieving logfile from device
###########################################
scp ${userid_device}@${deviceIP}:${data_dir_device}/${session_id}/pcaps/\*  ${data_dir_server}/${session_id}/
echo "${scriptname}: stored pcap output device at ${data_dir_server}/${session_id}"
