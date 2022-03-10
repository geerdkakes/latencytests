// configuration file read by 'index.js'
//
// please note this file is in javascript format

var config ={};

// Timing variables:
// maximum delay in which packets are still matched.
// be warned. The larger the delay (in useconds), the longer the algorith will run
config.max_delay = 500000; // 0,5 seconds

// maximum error allowed to match packets. The larger this value the longer the search
config.max_error = 500000; // 0,5 seconds

// window length in seconds to split the output in multiple files of length in seconds. define basename to add info to the output name
config.window_length = 300;

// offset to use if source and destination are not in sync
config.offset = 0;

// decoding combination
config.decoders = []

// ------------------------------------------------------------------------
// match array
//
// defines the headers which need to be matched from two packets
//
// currently only type match is supported.
// This array is used by the function match_array in 'compare_pcap.js'
config.match_array = [
    { type: "match", id: "protocol" },
    { type: "match", id:  "direction" },
    { type: "match", id: "ipHeader.dst.0" },
    { type: "match", id: "ipHeader.dst.1" },
    { type: "match", id: "ipHeader.dst.2" },
    { type: "match", id: "ipHeader.dst.3" },
    { type: "match", id:  "dataChksum" }
];

// ipHeader.dst.0,ipHeader.dst.1,ipHeader.dst.2,ipHeader.dst.3

// -----------------------------------------------------------------------
// header fields
//
// defines the header fiels used to store the compared packets in a csv file format
//
// used by 'compare_pcap.js'
config.header_fields = [
    {"id": "source_packetNr", "title": "source_packetNr"},
    {"id": "destination_packetNr", "title": "destination_packetNr"},
    {"id": "source_pcapPacketHeader.ts_sec", "title": "source_pcapPacketHeader.ts_sec"},
    {"id": "source_pcapPacketHeader.ts_usec", "title": "source_pcapPacketHeader.ts_usec"},
    {"id": "destination_pcapPacketHeader.ts_sec", "title": "destination_pcapPacketHeader.ts_sec"},
    {"id": "destination_pcapPacketHeader.ts_usec", "title": "destination_pcapPacketHeader.ts_usec"},
    {"id": "delay_usec", "title": "delay_usec"},
    {"id": "pcapPacketHeader.orig_len", "title": "pcapPacketHeader.orig_len"},
    {"id": "udpHeader.dest_port", "title": "udpHeader.dest_port"},
    {"id": "udpHeader.src_port", "title": "udpHeader.src_port"},
    {"id": "tcpHeader.dest_port", "title": "tcpHeader.dest_port"},
    {"id": "tcpHeader.src_port", "title": "tcpHeader.src_port"},
    {"id": "protocol", "title": "protocol"},
    {"id": "direction", "title": "direction"},
    {"id": "lost", "title": "lost"}
];

// -----------------------------------------------------------------------
// destination filter set
//
// Defines the filters to filter the packets at the destination.
// Extra objects can be added with field and value defined.
// All objects together in the level two array define one packet
// to be matched and form an AND relation.
//
// The operator can be one of the following values:
// eq: equal
// ne: not equal
// gt: greater than
// lt: less than
// ge: greater or equal
// le: less or equal
// contains: contains a value
//
// used by 'filter_packet' function defined in 'index.js'

default_filter = [
    [
        // identifies udp echo packets from device to serverv
        {type: "match", field: "protocol", value: "udp", operator: "eq"},
        {type: "match", field: "udpHeader.dest_port", value: 52000, operator: "ge"},
        {type: "match", field: "udpHeader.dest_port", value: 52010, operator: "le"},
        {type: "direction", value: "up" }
    ],
    [
        // identifies mqtt packets from device to serverv
        {type: "match", field: "protocol", value: "tcp", operator: "eq"},
        {type: "match", field: "tcpHeader.dest_port", value: 1883, operator: "eq"},
        {type: "match", field: "pcapPacketHeader.incl_len", value: "66", operator: "gt"},
        {type: "direction", value: "up" }
    ],
    [
        // identifies udp echo packets from server to device
        {type: "match", field: "protocol", value: "udp", operator: "eq"},
        {type: "match", field: "udpHeader.src_port", value: 52000, operator: "ge"},
        {type: "match", field: "udpHeader.src_port", value: 52010, operator: "le"},
        {type: "direction", value: "down" }
    ],
    [
        // identifies  mqtt packets from server to device
        {type: "match", field: "protocol", value: "tcp", operator: "eq"},
        {type: "match", field: "tcpHeader.src_port", value: 1883, operator: "eq"},
        {type: "match", field: "pcapPacketHeader.incl_len", value: "66", operator: "gt"},
        {type: "direction", value: "down" }
    ],
    [
        // identifies  iperf3 packets from server to device
        {type: "match", field: "protocol", value: "udp", operator: "eq"},
        {type: "match", field: "udpHeader.src_port", value: 5200, operator: "ge"},
        {type: "match", field: "udpHeader.src_port", value: 5251, operator: "le"},
        {type: "direction", value: "down" }
    ],
    [
        // identifies iperf3 packets from device to server
        {type: "match", field: "protocol", value: "udp", operator: "eq"},
        {type: "match", field: "udpHeader.dest_port", value: 5200, operator: "ge"},
        {type: "match", field: "udpHeader.dest_port", value: 5251, operator: "le"},
        {type: "direction", value: "up" }
    ]
];
// testrun with source from vehicle and destination for gNodeB

config.filter_set = default_filter;


// export the config object
module.exports = config;
