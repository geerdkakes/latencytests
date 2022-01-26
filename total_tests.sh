#!/usr/bin/env bash

#############################################
# Script to run perform the different testsessions
#  Variables:
#   -c <csv_filename> containing the test parameters to run the different tests 
#
#############################################

#############################################
# variables
#############################################
index=0
scriptname=$0
testonly=FALSE
lines_to_graph=""
udp_tests=0
mqtt_tests=0
iperf3_tests=0
source variables.sh
#############################################
# Cleanup function, run at exit of script
#############################################
function cleanup() {
  # we need to exit. First give some time for the processes to finish
  sleep 1
  echo "${scriptname}: processed $((index-1)) number of lines"
  echo "${scriptname}: exiting"
}
trap cleanup EXIT

#############################################
# interpret command line flags
# -a [all|test|analyse|graph] 
#############################################
while [ -n "$1" ]
do
    case "$1" in
        -c) csv_filename="$2"
            echo "${scriptname}: CSV filename to read: $csv_filename"
            shift ;;
        -a) action="$2"
            echo "${scriptname}: action: ${action}"
            shift ;;
        --) shift
            break ;;
        *) echo "${scriptname}: $1 is not an option";;
    esac
    shift
done

############################################
# check variable
############################################
function check_variable(){
    if [[ -v $1 ]]; then
      echo "....${1} was defined"
    else
      echo "....${1} not set, exiting"
      exit 1
    fi
}

#############################################
# all tasks to perform each run
#############################################
function run_test_tasks(){

    ############################
    # check precense of variables for testing
    ############################
    echo "${scriptname}: checking if called with correct variables"
    check_variable udp_test
    check_variable udp_data_size
    check_variable udp_interpacket_time
    check_variable udp_test_user
    check_variable udp_test_device_ip
    check_variable mqtt_test
    check_variable mqtt_data_size
    check_variable mqtt_interpacket_time
    check_variable mqtt_test_user
    check_variable mqtt_test_device_ip
    check_variable iperf3_test
    check_variable iperf3_test_user
    check_variable iperf3_test_device_ip
    check_variable iperf3_direction
    check_variable test_duration
    check_variable session_id
    check_variable iperf3_mtu_size
    check_variable iperf3_server_ip
    check_variable iperf3_streams
    check_variable iperf3_protocol
    check_variable iperf3_bitrate
    check_variable pcap_server1_ip
    check_variable server_interface
    check_variable modem_prefix_ip
    check_variable pcap_device1_user
    check_variable pcap_device1
    check_variable pcap_device1_ip
    check_variable pcap_server1_ip
    check_variable pcap_device1_ports
    check_variable pcap_device1_snaplen
    check_variable pcap_device1_protocols
    check_variable iperf3_port

    echo
    echo "${scriptname}: running test session ${session_id} for ${test_duration} seconds"

    # start recording pcaps
    if [ "${pcap_device1^^}" =  "TRUE" ] ; then
        echo "${scriptname}: starting pcap logging device 1"
        ./record_pcaps.sh -s ${session_id} -t ${test_duration} -test_id dev1 -d_user ${pcap_device1_user} -d_ip ${pcap_device1_ip} -d_ip_modem_prefix ${modem_prefix_ip} -s_if ${server_interface} -s_ip ${pcap_server1_ip} -snaplen ${pcap_device1_snaplen} -ports ${pcap_device1_ports} -protocols ${pcap_device1_protocols} &
    fi
    if [ "${pcap_device2^^}" =  "TRUE" ] ; then
        echo "${scriptname}: starting pcap logging device 2"
        ./record_pcaps.sh -s ${session_id} -t ${test_duration} -test_id dev2 -d_user ${pcap_device2_user} -d_ip ${pcap_device2_ip} -d_ip_modem_prefix ${modem_prefix_ip} -s_if ${server_interface} -s_ip ${pcap_server2_ip} -snaplen ${pcap_device2_snaplen} -ports ${pcap_device2_ports} -protocols ${pcap_device2_protocols} &
    fi

    # start udp tests
    if [ "${udp_test^^}" =  "TRUE" ] ; then
        echo "${scriptname}: starting udp tests"
        ./UDP_echo_test.sh -b ${udp_data_size} -t ${test_duration} -s_ip ${udp_server_ip} -d_ip ${udp_test_device_ip} -i ${udp_interpacket_time} -d_user ${udp_test_user} -s ${session_id} &
    fi

    # start mqtt tests
    if [ "${mqtt_test^^}" =  "TRUE" ] ; then
        echo "${scriptname}: starting mqtt tests"
        ./MQTT_test.sh -b ${mqtt_data_size} -t ${test_duration} -s_ip ${mqtt_server_ip} -d_ip ${mqtt_test_device_ip} -i ${mqtt_interpacket_time} -d_user ${mqtt_test_user} -s ${session_id} &
    fi

    # start iperf3 tests
    if [ "${iperf3_test^^}" =  "TRUE" ] ; then
        echo "${scriptname}: starting iperf3 tests"
        ./run_iperf3.sh -s ${session_id} -M ${iperf3_mtu_size} -bitrate ${iperf3_bitrate} -s_ip ${iperf3_server_ip} -d_ip ${iperf3_test_device_ip} -t ${test_duration} -d ${iperf3_direction} -d_user ${iperf3_test_user} -protocol ${iperf3_protocol} -streams ${iperf3_streams} -port ${iperf3_port} &
    fi

    sleep $((test_duration+10))
}
#############################################
# check bash version
#############################################
function check_bash_version() {
    local major=${1:-4}
    local minor=$2
    local num_re='^[0-9]+$'
    echo "${scriptname}: checking bash version... (minimal ${major}.${minor})"
    if [[ ! $major =~ $num_re ]] || [[ $minor && ! $minor =~ $num_re ]]; then
        printf '%s\n' "${scriptname}: ERROR: version numbers should be numeric"
        exit 1
    fi
    if [[ $minor ]]; then
        local bv=${BASH_VERSINFO[0]}${BASH_VERSINFO[1]}
        local vstring=$major.$minor
        local vnum=$major$minor
    else
        local bv=${BASH_VERSINFO[0]}
        local vstring=$major
        local vnum=$major
    fi
    ((bv < vnum)) && {
        printf '%s\n' "${scriptname}: ERROR: Need Bash version $vstring or above, your version is ${BASH_VERSINFO[0]}.${BASH_VERSINFO[1]}"
        exit 1
    }
}

#############################################
# read csv file and interpret variables
#############################################
function read_csv(){
    
    script_to_run=$1
    # first read csv file in an array
    arr_csv=() 
    while IFS= read -r line  || [ -n "$line" ]
    do
        arr_csv+=("$line")
    done < ${csv_filename}


    for line in "${arr_csv[@]}"
    do
        # remove carriage return
        line=$(echo ${line} | sed 's/\r$//')
        # read line in array with separator ';'
        readarray "-td;" a <<<"$line;"
        # delete last element invoked by the extra ';' added when reading the array
        unset 'a[-1]'
        if [ "${index}" = "0" ] ; then
           # store first line in header variable, needed to set each variable
           header=("${a[@]}")
        else
            # loop over elements and set variable using earlier stored header array
            i=0
            for record in "${a[@]}"; do
                declare "${header[i]}=${record}"
                ((i++))
            done
            # finieshed looping over elements on single line, now run tasks for this line
            ${script_to_run}
        fi
        ((index++))
        echo "${scriptname}: Line $((index-1)) finished processing"
    done
}

function analyse_tests() {
    ./run_pcap_analysis.sh -s ${session_id}
}
function collect_lines() {
    if [ -f "${data_dir_server}/${session_id}/compare_total.csv" ]; then
        echo "${scriptname}: removing previous collection: ${data_dir_server}/${session_id}/compare_total.csv"
        rm ${data_dir_server}/${session_id}/compare_total.csv
    fi
    csv_compare_files=(${data_dir_server}/${session_id}/compare_*.csv)
    echo "${scriptname}: collecting comparison result of session: ${session_id} to ${data_dir_server}/${session_id}/compare_total.csv"
    head -1 ${csv_compare_files[0]} > ${data_dir_server}/${session_id}/compare_total.csv
    for file in ${csv_compare_files[@]}; do
        echo "${scriptname}: adding ${file}"
        tail -n +2 ${file} >> ${data_dir_server}/${session_id}/compare_total.csv
    done
    lines_to_graph="${lines_to_graph} ${data_dir_server}/${session_id}/compare_total.csv:${session_id}"

    # check which tests have run during all sessions
    if [ "${udp_test^^}" =  "TRUE" ] ; then
        ((udp_tests++))
    fi
    if [ "${mqtt_test^^}" =  "TRUE" ] ; then
        ((mqtt_tests++))
    fi
    if [ "${iperf3_test^^}" =  "TRUE" ] ; then
        ((iperf3_tests++))
    fi

    echo "${scriptname}: lines to graph: ${lines_to_graph}"
}
function graph_tests() {
    protocols_to_graph=""
    total_sessions=$((index-1))
    echo "${scriptname}: graphing ${total_sessions} sessions"
    if [ "${udp_tests}" -eq "${total_sessions}" ]; then
        if [ "${protocols_to_graph}" = "" ]; then
            protocols_to_graph="udp"
        else
            protocols_to_graph=":udp"
        fi
    fi
    if [ "${mqtt_tests}" -eq "${total_sessions}" ]; then
        if [ "${protocols_to_graph}" = "" ]; then
            protocols_to_graph="mqtt"
        else
            protocols_to_graph=":mqtt"
        fi
    fi
    if [ "${iperf3_tests}" -eq "${total_sessions}" ]; then
        if [ "${protocols_to_graph}" = "" ]; then
            protocols_to_graph="iperf3"
        else
            protocols_to_graph=":iperf3"
        fi
    fi
    lines_to_graph="${protocols_to_graph} ${lines_to_graph}"
    echo "${scriptname}: starting graph with argument: ${lines_to_graph}"
    export data_dir_server="${data_dir_server}"
    echo " calling graph_histogram.py with env data_dir_server: ${data_dir_server} and argument: ${lines_to_graph}"
    ./graph_histogram.py ${lines_to_graph}
}

#############################################
# start main program
#############################################

check_bash_version 4 2

if [ "${action^^}" =  "ALL" ] || [ "${action^^}" =  "TEST" ] ; then
    read_csv run_test_tasks
    sleep 20
fi
if [ "${action^^}" =  "ALL" ] || [ "${action^^}" =  "ANALYSE" ] ; then
    read_csv analyse_tests
fi
if [ "${action^^}" =  "ALL" ] || [ "${action^^}" =  "GRAPH" ] ; then
    sleep 5
    read_csv collect_lines
    sleep 10
    graph_tests
fi