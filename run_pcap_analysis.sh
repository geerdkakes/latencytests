#!/usr/bin/env bash

#############################################
# fixed variables
#############################################
source variables.sh
basename_a="device"
basename_b="server"
scriptname=$0
#############################################
# interpret command line flags
#############################################
while [ -n "$1" ]
do
    case "$1" in
        -s) session_id="$2"
            echo "${scriptname} session id: $session_id"
            shift ;;
        -d) dev_id="$2"
            echo "${scriptname} device id: $dev_id"
            shift ;;
        --) shift
            break ;;
        *) echo "${scriptname} $1 is not an option";;
    esac
    shift
done


#############################################
# dynamic variables
#############################################
if [ "${session_id}" = "" ]; then
  pcap_dir="${data_dir_server}"
else
  pcap_dir="${data_dir_server}/${session_id}"
fi

if [ ! -d "${pcap_dir}" ] ; then
    echo "${scriptname}: Directory ${pcap_dir} does not exist"
fi
devs=($(ls ${pcap_dir} | grep .pcap | sed 's/\(.*\)_\(.*\)_.*_.*.pcap/\2/' | sort | uniq))


#############################################
# find and convert server csv files
#############################################
echo "decoding pcap files"
for dev in ${devs[@]}; do
    if [ ! -z $dev_id ] && [[ "${dev_id}" != "${dev}" ]]; then
        echo "${scriptname}: device id ${dev_id} specified to analyse but not matched to ${dev}, continuing"
        continue
    fi
    echo "${scriptname}: processing dev: ${dev}"
    echo "${scriptname}: ...............processing server side pcaps"
    echo ""
    for filename in ${pcap_dir}/${basename_b}_${dev}*.pcap; do
        [ -e "$filename" ] || continue
        echo ${scriptname}: decoding $filename
        echo node --max-old-space-size=14000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -i ${filename} -s true -b server${dev}
        node --max-old-space-size=14000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -i ${filename} -s true -b server${dev}
    done
    echo "${scriptname}: ...............processing device side pcaps"
    echo ""
    for filename in ${pcap_dir}/${basename_a}_${dev}*.pcap; do
        [ -e "$filename" ] || continue
        echo ${scriptname}: decoding $filename
        echo node --max-old-space-size=14000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -i ${filename} -s true -b device${dev}
        node --max-old-space-size=14000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -i ${filename} -s true -b device${dev}
    done
done

#############################################
# matching csv files and comparing them
#############################################
echo "matching decoded files"
for dev in ${devs[@]}; do 
    if [ ! -z $dev_id ] && [[ "${dev_id}" != "${dev}" ]]; then
        echo "${scriptname}: device id ${dev_id} specified to analyse but not matched to ${dev}, continuing"
        continue
    fi
    echo "${scriptname}: processing dev: ${dev}"
    for filename in ${pcap_dir}/*${basename_a}${dev}.csv; do
        echo "${scriptname}: for file: $filename:"
        if [ ! -e "$filename" ]; then
            echo "does not exist"
            continue
        fi
        date_str="`/usr/bin/basename $filename | sed 's/\(.*\..*\..*\)_\(.*\..*\..*\)-\(.*..*..*\)_\(.*\)\.\(.*\)/\1/'`" # 2021.2.3
        echo data_str: $date_str
        time_lower="`/usr/bin/basename $filename | sed 's/\(.*\..*\..*\)_\(.*\..*\..*\)-\(.*..*..*\)_\(.*\)\.\(.*\)/\2/'`" # 10.20.0
        echo time_lower: $time_lower
        time_upper="`/usr/bin/basename $filename | sed 's/\(.*\..*\..*\)_\(.*\..*\..*\)-\(.*..*..*\)_\(.*\)\.\(.*\)/\3/'`" # 10.25.0
        echo time_upper: $time_upper
        filename_a="${pcap_dir}/${date_str}_${time_lower}-${time_upper}_${basename_a}${dev}.csv"
        filename_b="${pcap_dir}/${date_str}_${time_lower}-${time_upper}_${basename_b}${dev}.csv"
        filename_result="${pcap_dir}/compare_${date_str}_${time_lower}-${time_upper}_${basename_a}${dev}-${basename_b}.csv"
        
        # checking if filenames exist, if not continue to next file
        [ -e "$filename_a" ] || continue 
        [ -e "$filename_b" ] || continue
        echo "found matching filename: $filename_b"
        echo  "comparing files and storing result in: ${filename_result}"
        node --max-old-space-size=12000 "${pcap_analysis_app}" -c ${pcap_analysis_config_file} -r ${filename_result} --compare=${filename_a},${filename_b}
        echo
    done
done