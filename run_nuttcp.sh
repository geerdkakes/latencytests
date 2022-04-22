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
MTU=1400
time=10
testdate="$(date +"%m-%d-%y_%H.%M")"
session_id="$(date +"%s")"
streams="1"
udp=""
scriptname=$0
nuttcp_port=5210
#############################################
# interpret command line flags
#############################################
while [ -n "$1" ]
do
    case "$1" in
        -s) session_id="$2"
            echo "${scriptname}: session id: $session_id"
            shift ;;
        -M) MTU="$2"
            echo "${scriptname}: MTU size parsed: ${MTU}"
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
        -d) direction="$2"
            echo "${scriptname}: Traffic direction: ${direction}"
            shift ;;
        -d_user) userid_device="$2"
            echo "${scriptname}: userid used at device: ${userid_device}"
            shift ;;
        -bitrate) bitrate="$2"
            echo "${scriptname}: bitrate used: ${bitrate}"
            shift ;;
        -streams) streams="$2"
            echo "${scriptname}: streams used: ${streams}"
            shift ;;
        -protocol) protocol="$2"
            echo "${scriptname}: protocol used: ${protocol}"
            shift ;;
        -controlport) nuttcp_controlport="$2"
            echo "${scriptname}: nuttcp_controlport used: ${nuttcp_controlport}"
            shift ;;
        -dataport) nuttcp_dataport="$2"
            echo "${scriptname}: nuttcp_dataport used: ${nuttcp_dataport}"
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
datalength=$((MTU - 66))
DATALENGTH=$((MTU - 56))
if [ "${direction}" = "up" ]; then
  dir_var="-t"
else
  dir_var="-r"
fi

if [ "${protocol}" = "udp" ]; then
  udp_tcp_specific="-u -l${datalength}"
fi
if [ "${protocol}" = "tcp" ]; then
  udp_tcp_specific="-w${datalength}b"
fi
if [ "${bitrate}" = "" ]; then
    echo "no bitrate specified"
    bitrateoption=""
else
    bitrateoption="-R${bitrate}"
fi

###########################################
# create data directories with session id
###########################################
mkdir -p ${data_dir_server}/${session_id}
ssh ${userid_device}@${deviceIP} "/usr/bin/mkdir -p ${data_dir_device}/${session_id}"

######################################################################
# nuttcp test with the following parameters:
#  -l1334               :(for MTU of 1400, MTU = 66 + data length) use with udp
#  -w1334b              :(MTU = 66 + window size) use with tcp
#  -D                   :disable Nagle algorithm (TCP_NODELAY)
#  -R<bitrate>
#  -T<time to test>     :time in seconds to run test
#  -r                   :receive traffic
#  -t                   :transmit traffic
#  -u                   : specify to test using udp
#  -1                   : one shot server
#  -S                   : Server mode
#  <ip address>
######################################################################
echo "${scriptname}: starting serverside nuttcp test"


# start server side
echo "${scriptname}: start server side nuttcp"
echo "${nuttcp_app} -1 -P${nuttcp_controlport}"
${nuttcp_app} -1 -P${nuttcp_controlport}
sleep 1

echo "${scriptname}: running client side nuttcp test with MTU: ${MTU} MSS window: ${MSS} Datalenth: ${DATALENGTH} serverIP ${serverIP} and port ${nuttcp_port}"
echo "${scriptname}: ssh ${userid_device}@${deviceIP} \"${nuttcp_app} -o -P${nuttcp_controlport} -p${nuttcp_dataport} -T${time} ${dir_var} -N${streams} ${bitrateoption} ${udp_tcp_specific} ${serverIP} > ${data_dir_device}/${session_id}/device_nuttcp_${testdate}.log\""
ssh ${userid_device}@${deviceIP} "date +'startetime:%s' > ${data_dir_device}/${session_id}/device_nuttcp_${testdate}.log"
ssh ${userid_device}@${deviceIP} "direction:${direction} >> ${data_dir_device}/${session_id}/device_nuttcp_${testdate}.log"
ssh ${userid_device}@${deviceIP} "title:${session_id} >> ${data_dir_device}/${session_id}/device_nuttcp_${testdate}.log"
ssh ${userid_device}@${deviceIP} "${nuttcp_app} -o -P${nuttcp_controlport} -p${nuttcp_dataport} -T${time} ${dir_var} -N${streams} ${bitrateoption} ${udp_tcp_specific} ${serverIP} >> ${data_dir_device}/${session_id}/device_nuttcp_${testdate}.log"
if [ ${?} -eq 1 ]; then
    echo "${scriptname}:  Error while connecting from client site to nuttcp server"
else
    echo "${scriptname}:  Finished nuttcp test"
fi
sleep 3


##########################################
# retrieve device logfile 
##########################################
scp ${userid_device}@${deviceIP}:${data_dir_device}/${session_id}/device_nuttcp_${testdate}.log  ${data_dir_server}/${session_id}/
echo "${scriptname}: stored nuttcp output at ${data_dir_server}/${session_id}/device_nuttcp_${testdate}.log"
