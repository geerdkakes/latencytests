#!/usr/bin/env bash

#############################################
# Script to run an iperf3 session on a remote host
#  Variables:
#   -s <session id>
#   -M <MTU size>
#   -s_ip server IP to which the iperf3 client will connect
#   -d_ip device IP at which the device can be reached (preferably a fixed connection)
#   -t time in seconds to run the trial
#   -d up | down (up: traffic generated by device, down: traffic generated by server)
#   -d_user <userid> from device
#   -perc <percentage> percentage used from radio
#############################################

######################
# config for 40MHz 4 
# 50% downlink: iperf3 -c ip_Addr -u -b 100000000 -R -p 5203 -l 1344 -t 120
# 80% downlink: iperf3 -c ip_Addr -u -b 60000000 -R -p 5203 -l 1344 -t 120 -P 2
######################

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
iperf3_port=5210
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
        -test_id) testID="$2"
            echo "${scriptname}: testID set to: ${testID}"
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
        -port) iperf3_port="$2"
            echo "${scriptname}: iperf3_port used: ${iperf3_port}"
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
MSS=$((MTU - 44))
DATALENGTH=$((MTU - 56))
if [ "${direction}" = "up" ]; then
  dir_var=""
else
  dir_var="-R"
fi

if [ "${protocol}" = "udp" ]; then
  udp_tcp_specific="-u"
fi
if [ "${protocol}" = "tcp" ]; then
  udp_tcp_specific="-M ${MSS}"
fi
if [ "${bitrate}" = "" ]; then
    echo "no bitrate specified"
    bitrateoption=""
else
    bitrateoption="-b ${bitrate}"
fi

###########################################
# create data directories with session id
###########################################
mkdir -p ${data_dir_server}/${session_id}
ssh ${userid_device}@${deviceIP} "mkdir -p ${data_dir_device}/${session_id}"

######################################################################
# iperf3 test with the following parameters:
#  -l 1344              :(for MTU of 1400, MTU = 56 + data length)
#  -M 1356              :(MTU = 44 + tcp MSS)
#  -N                   :disable Nagle algorithm
#  -b <bitrate>
#  -t <time to test>    :time in seconds to run test
#  -O 1                 :seconds to ommit before starting measurements (skip TCP slow start)
#  -J                   :Json output for later processing
#  -c <ip address>
#  -u                   : specify to test using udp
######################################################################
echo "${scriptname}: starting serverside iperf test"
echo "${scriptname}: ${iperf3_app} -s -1 -J  -p ${iperf3_port} -i 10 > ${data_dir_server}/${session_id}/server${testID}_iperf3_${testdate}.json"
result=1

while [ ${result} -eq 1 ]; do
    ${iperf3_app} -s -1 -J -p ${iperf3_port} -i 10 > ${data_dir_server}/${session_id}/server${testID}_iperf3_${testdate}.json &
    iperf_PID=$!
    sleep 1
    kill -0 $iperf_PID
    result=$?
    if [ ${result} -eq 1 ]; then
        echo "${scriptname}:  Error starting server side iperf3 session. Retrying in 1 second"
    else
        echo "${scriptname}:  Started server side iperf3."
        break
    fi
done

echo "${scriptname}: running client side iperf test with MTU: ${MTU} MSS window: ${MSS} Datalenth: ${DATALENGTH} serverIP ${serverIP}, port ${iperf3_port} testID: ${testID}"
echo "${scriptname}: ssh ${userid_device}@${deviceIP} \"${iperf3_app} -p ${iperf3_port} -c ${serverIP} -l ${DATALENGTH} -N -t ${time} -T ${session_id} -O 1 -J ${dir_var} -i 10 -P ${streams} ${bitrateoption} ${udp_tcp_specific} > ${data_dir_device}/${session_id}/device${testID}_iperf3_${testdate}.json\""
ssh ${userid_device}@${deviceIP} "${iperf3_app} -c ${serverIP} -p ${iperf3_port} -l ${DATALENGTH} -N -t ${time} -T ${session_id} -O 1 -J ${dir_var} -i 10 -P ${streams} ${bitrateoption} ${udp_tcp_specific} > ${data_dir_device}/${session_id}/device${testID}_iperf3_${testdate}.json"
if [ ${?} -eq 1 ]; then
    echo "${scriptname}:  Error while connecting from client site to iperf3 server"
else
    echo "${scriptname}:  Finished iperf3 test"
fi
sleep 3
echo "${scriptname}:  Checking if server session closed as should"
kill -0 $iperf_PID
result=$?
if [ ${result} -eq 1 ]; then
    echo "${scriptname}:  Iperf session has closed down"
else
    echo "${scriptname}:  iperf3 session on server still running!!!"
    echo "${scriptname}:  closing server iperf3 session for session_id $session_id"
    kill $iperf_PID
fi
##########################################
# retrieve device logfile 
##########################################
scp ${userid_device}@${deviceIP}:${data_dir_device}/${session_id}/device${testID}_iperf3_${testdate}.json  ${data_dir_server}/${session_id}/
echo "${scriptname}: stored iperf3 output at ${data_dir_server}/${session_id}/device${testID}_iperf3_${testdate}.json"
