# variables used by script.

# rename variabes.skel.sh to variables.sh and change the variable values


# Directories to store data files
data_dir_device="/tmp/datadir"
data_dir_server="/data/datadir"

# Path with configuration file pcap analysis
pcap_analysis_config_file="/data/config_pcap_analysis.js"

# Path to pcap analysis tool
pcap_analysis_app="/usr/local/analyse_pcap/index.js"

# Path to MQTT test app on device:
mqtt_delay_app="/usr/local/mqtt-delay/server.js"

# Path to UDP Echo tool
udp_echo_app_server="/usr/local/ServerSocketTCP_UDP/udp_server.js"
udp_app_receive="/usr/local/ServerSocketTCP_UDP/udp_server.js"
udp_echo_app_device="/usr/local/ServerSocketTCP_UDP/udp_client.js"
udp_app_send="/usr/local/ServerSocketTCP_UDP/udp_client.js"

# Path to iperf
iperf2_app="/usr/local/iperf2/src/iperf"
iperf3_app="/usr/local/iperf3/src/iperf3"