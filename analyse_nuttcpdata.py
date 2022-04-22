#!/usr/bin/env python3
from time import time
from numpy.lib.shape_base import column_stack
import pandas as pd
import json
import numpy as np
import matplotlib.pyplot as plt
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import sys
import os
from datetime import datetime
import re
# run using: ./analyse_iperfdata.py ../datadir/Low_Latency_Test_Eindhoven_20211129_042742_Eindhoven_BIC_Usage_of_Radio_Resource_Monitoring_20211129_144832.csv ../datadir/20211129_02*/*.json

rb_blocks_file=sys.argv[1]
data_files=sys.argv[2:]

    # example samples:
    # downlink:
    #   "sum": {
    #     "start": 9.9e-05,
    #     "end": 0.999976,
    #     "seconds": 1.0000749826431274,
    #     "bytes": 12426624,          <- these are the bytes received
    #     "bits_per_second": 99405538.30999601,
    #     "jitter_ms": 1.4391494853445173,
    #     "lost_packets": 60,
    #     "packets": 9306,
    #     "lost_percent": 0.6447453255963894,
    #     "omitted": false,
    #     "sender": false
    #   }
    # Uplink:
    #       "sum": {
    #     "start": 3.99992,
    #     "end": 4.999968,
    #     "seconds": 1.000048041343689,
    #     "bytes": 2905728,                <- these are the bytes send (might not be received)
    #     "bits_per_second": 23244707.293027986,
    #     "packets": 2162,
    #     "omitted": false,
    #     "sender": true
    #   }

#############################################################################################
# Load json output data from iperf
# For each interval the sumbits_per_second is used to calculate the bytes, kbytes and Mbytes per second
# timestamp is added to each interval record with microseond accuracy
# a pandas dataframe is returned with the data
#
# this function is tested with iperf tcp
#############################################################################################
def load_iperf_json(filename):
    with open(filename,'r') as f:
        data = json.loads(f.read())
    if data['start']['test_start']['protocol'] == 'TCP':
        print("found tcp ")
        if "end" in data:
            if "sum" in data['end']:
                data['end']['sum'] = data['end']['sum_received']
                data['end']['sum']['packets'] = data['end']['sum_sent']['bytes'] / data['start']['test_start']['blksize']
                data['end']['sum']['lost_bytes'] = data['end']['sum_sent']['bytes'] - data['end']['sum_received']['bytes']
                data['end']['sum']['lost_packets'] = data['end']['sum']['lost_bytes'] / data['start']['test_start']['blksize']
                data['end']['sum']['lost_percent'] = data['end']['sum']['lost_packets'] / data['end']['sum']['packets']
        
    df = pd.json_normalize(data, record_path =['intervals'], 
        meta=[

            ['start', 'timestamp', 'timesecs'],
            ['start', 'timestamp', 'time'],
            ['start', 'test_start', 'protocol'],
            ['start', 'test_start', 'reverse'],
            ['start', 'test_start', 'blksize'],
            ['end', 'sum', 'seconds'],
            ['end', 'sum', 'bytes'],
            ['end', 'sum', 'bits_per_second'],
            ['end', 'sum', 'lost_packets'],
            ['end', 'sum', 'packets'],
            ['end', 'sum', 'lost_percent'],
            ['title']

        ])

    df['timestamp_microsec'] = (df['start.timestamp.timesecs'] + df['sum.start'])*1000000
    # add an hour to align with resource block data
    df['timestamp_milisec'] = df['timestamp_microsec'] / 1000 + 7200000
    df['timestamp'] = df['timestamp_milisec'].apply(np.int64)
    df['kbit_per_second'] = df['sum.bits_per_second'] / 1024
    if data['start']['test_start']['reverse'] == 0:
        # upload of data. we record the send data rate
        df['up_Mbit_per_second'] = df['kbit_per_second'] / 1024
        df['down_Mbit_per_second'] = 0
        df['direction'] = 'up'
    else:
        # download of data
        df['down_Mbit_per_second'] = df['kbit_per_second'] / 1024
        df['up_Mbit_per_second'] = 0
        df['direction'] = 'down'
    # drop columns not needed
    df = df.drop(columns=[ 'timestamp_microsec', 'timestamp_milisec', 'streams'])
    df.set_index('timestamp')
    return df
#############################################################################################
# Load csv output data from iperf2
# For each interval the bitrate and packet loss is determined
# 
# a pandas dataframe is returned with the data
#
# this function is tested with iperf2 using udp
#############################################################################################
def load_iperf_csv(filename):
    names= [
        "datetime_str",
        "source_ip",
        "source_port",
        "dest_ip",
        "dest_port",
        "iperf_proc_num",
        "time_interval",
        "data_transferred_bytes",
        "bits_per_second",
        "jitter_ms",
        "num_lost_pckts",
        "packets_send",
        "perc_lost",
        "num_out_of_order"
    ]

    # convert datetime string to timestamp
    # 20220315120825
    def date_time_str_to_timestamp(number):
        year = int(str(number)[:4])
        month = int(str(number)[4:6])
        day = int(str(number)[6:8])
        hour = int(str(number)[8:10])
        minute = int(str(number)[10:12])
        seconds = int(str(number)[12:])
        found_datetime = datetime(year, month, day, hour, minute, seconds)
        return datetime.timestamp(found_datetime)
    

    df = pd.read_csv(filename,names=names)
    df['direction'] = "down"
    df.loc[df['source_port'] > 10000, 'direction'] = "up"
    df['timestamp']  = df['datetime_str'].apply(date_time_str_to_timestamp)
    df['timestamp'] = (df['timestamp'] * 1000  + 7200000 ).apply(np.int64)
    df['kbit_per_second'] = df['bits_per_second'] / 1024
    df['down_Mbit_per_second'] = 0
    df['up_Mbit_per_second'] = 0
    df.loc[df['direction'] == 'down', 'down_Mbit_per_second'] = df.loc[df['direction'] == 'down', 'kbit_per_second']/1024
    df.loc[df['direction'] == 'up', 'up_Mbit_per_second'] = df.loc[df['direction'] == 'up', 'kbit_per_second']/1024
    df = df.drop(columns=[ 'source_ip', 'source_port', 'dest_ip', 'dest_port', 'iperf_proc_num', 'time_interval'])
    df.set_index('timestamp')
    return df

#############################################################################################
# Load nuttcp output data
# The output data needs to begin with a timestamp, following with the output data generated by nuttcp
# nuttcp is run with the extra -o flag to generate additional output
# nuttcp is only tested while using UDP transfers
#############################################################################################
def load_nuttcp(filename):
    fields = ['text']
    df = pd.read_csv(filename, names=fields, skiprows=3)

    df[["volume", "duration", "bandwidth", "tx_perc", "rx_perc", "dropped_pckts", "received_pckts", "perc_lost", "latency"]] = df["text"].str.extract(r'([0-9]*[.]?[0-9]+)\sMB\s\/\s([0-9]*[.]?[0-9]+)\ssec\s=\s+([0-9]*[.]?[0-9]+)\sMbps\s([^_]+)\s%TX\s([^_]+)\s%RX\s([^_ ]+)\s\/\s([^_ ]+)\sdrop\/pkt\s([0-9]*[.]?[0-9]+)\s%loss\s([0-9]*[.]?[0-9]+)\smsAvgOWD')
    df = df.drop(columns=[ 'text'])

    # read file to get start time (should be on first line)
    s = open(filename, 'r')                            
    contents = s.read()                                
    starttime  = int(re.findall(r'(?:startetime|starttime):([0-9]*)', contents)[0])

    direction  = re.findall(r'direction:([a-z]*)', contents)[0]
    title = re.findall(r'title:([a-z0-9_]*)', contents)[0]

    df_expanding_empty = True
    for index, row in df.iterrows():
        # for each row expand dataframe
        endtime = starttime + float(row['duration'])
        
        for time in range(starttime, int(endtime)):
            # timestamp in miliseconds, two hours shifted:
            timestamp = (time + 7200) * 1000
            percentage_lost = float(row['perc_lost'])
            bandwidth_Mbps = float(row['bandwidth'])
            up_Mbit_per_second = 0
            up_Mbit_per_second_received = 0
            up_Mbit_per_second_send = 0
            down_Mbit_per_second = 0
            down_Mbit_per_second_received = 0
            down_Mbit_per_second_send = 0
            if direction == 'up':
                up_Mbit_per_second = bandwidth_Mbps
                up_Mbit_per_second_received = bandwidth_Mbps
                up_Mbit_per_second_send = bandwidth_Mbps / ((100-percentage_lost)/100)
            if direction == 'down':
                down_Mbit_per_second = bandwidth_Mbps
                down_Mbit_per_second_received = bandwidth_Mbps
                down_Mbit_per_second_send = bandwidth_Mbps / ((100-percentage_lost)/100)
            packets_lost = int(row['dropped_pckts'])
            total_packets = int(row['received_pckts']) + packets_lost
            
            expanding_array = {
                'up_Mbit_per_second': [up_Mbit_per_second],
                'up_Mbit_per_second_send': [up_Mbit_per_second_send],
                'up_Mbit_per_second_received': [up_Mbit_per_second_received],
                'down_Mbit_per_second': [down_Mbit_per_second],
                'down_Mbit_per_second_received': [down_Mbit_per_second_received],
                'down_Mbit_per_second_send': [down_Mbit_per_second_send],
                'bandwidth_Mbps': [bandwidth_Mbps],
                'packets_lost': [packets_lost],
                'packets_send': [total_packets],
                'percentage_lost': [percentage_lost],
                'timestamp': [timestamp],
                'direction': [direction],
                'title': [title]
            }
           
            if df_expanding_empty:
                df_expanding = pd.DataFrame.from_dict(expanding_array)
                df_expanding_empty = False
            else:
                df_expanding = df_expanding.append(pd.DataFrame.from_dict(expanding_array),ignore_index=True)

    return df_expanding
#############################################################################################
# Load csv file exported by U2020 from Huawei
# the file contains per second the amound of resource blocks used for uplink and downlink
# output: dataframe containing:
#     timestamp:                microsecond timestamp, also the index
#     Downlink Used RB Num:     Resouce blocks used in downlink
#     Uplink Used RB Num:       Resource blocks used in uplink
#     NR DU Cell ID:            cell id
#     DateTime:                 date time field with second accuracy
#############################################################################################
def load_resource_blocks(filename):
    df = pd.read_csv(filename, skiprows=9)

    # DateTime format in file: '2021-11-25 09:10:25 (4)'
    # Convert to: '2021-11-25 09:10:25' and store miliseconds in separate column
    df['DateTime'] = df['Time'].replace({r'(.*)\s\((\d+)\)' : r'\g<1>'}, regex=True)
    df['miliseconds'] = df['Time'].replace({r'(.*)\s\((\d+)\)' : r'\g<2>'}, regex=True).astype(np.int64)

    # create datetime field with second accuracy
    df['DateTime'] = pd.to_datetime(df['DateTime'],format='%Y-%m-%d %H:%M:%S DST')

    # create timestamp in miliseconds:
    df['nanoseconds'] = df['miliseconds'] * 1000000
    df['timestamp_nanoseconds'] = df.DateTime.values.astype(np.int64) + df['nanoseconds']
    df['timestamp_miliseconds'] = df['timestamp_nanoseconds'] / 1000000
    df['timestamp'] = df['timestamp_miliseconds'].apply(np.int64)
    df.set_index('timestamp')

    # drop columns not needed
    df = df.drop(columns=['Time', 'miliseconds', 'nanoseconds', 'timestamp_nanoseconds', 
                        'timestamp_miliseconds', 'CN Operator Index', 'PLMN Downlink Used RB Num', 
                        'PLMN Uplink Used RB Num', 'NR DU Cell TRP ID', 'Serial No.'])

    # return dataframe
    return df
#############################################################################################
# Load modem output, generated by script generating the data
# data should be of csv format, containing the correct headers:
#
#  timestamp,lat,lon,cell_type,state,technology,duplex_mode,mcc,mnc,cell_id,pc_id,tac,arfcn,band,nr_dl_bandwidth,rsrp,rsrq,sinr,scs,srxlev 
#
# a pandas dataframe is returned with the data
#############################################################################################

def load_modem_csv(filename):
    try:
        df = pd.read_csv(filename)
    except FileNotFoundError:
        print("File Doesn't Exist: " + filename)
    else:
        df.set_index('timestamp')
        return df


#############################################################################################
# merge dataframes. df_sub is merged in df_data
# merging is done based on timestamp
#
# a pandas dataframe is returned with the data
#
#############################################################################################
def merge_dataframes(df_sub, df_data):
    
    length_sub = df_sub.shape[0]
    length_main = df_data.shape[0]
    
    i_s = 0
    i_d = 0
    
    start_s = 0
    start_d = 0
    
    end_s = 0
    end_d = 0
    
    # loop over data array to find start and end
    while i_s < length_sub and i_d < length_main:
        if abs(df_sub.iloc[i_s]['timestamp'] - df_data.iloc[i_d]['timestamp']) <= 1500:
            start_s = i_s
            start_d = i_d
            break
        if df_sub.iloc[i_s]['timestamp'] < df_data.iloc[i_d]['timestamp']:
            i_s += 1
        else:
            i_d += 1
    
    i_s = length_sub - 1
    i_d = length_main - 1

    while i_s >=0 and i_d >= 0:
        if abs(df_sub.iloc[i_s]['timestamp'] - df_data.iloc[i_d]['timestamp']) <= 1500:
            end_s = i_s
            end_d = i_d
            break
        if df_sub.iloc[i_s]['timestamp'] < df_data.iloc[i_d]['timestamp']:
            i_d -= 1
        else:
            i_s -= 1


    df_sub = df_sub.iloc[start_s:end_s]
    df_data = df_data.iloc[start_d:end_d]
    
    columns_to_copy = []
    matched_array = []
    for col in df_sub.columns:
        if col != "timestamp" and col != "DateTime":
            columns_to_copy.append(col)
            matched_array.append([])

    # find the matching timestaps in df_sub and copy the columns of interest in a seperate array
    for index, row in df_data.iterrows():
        index_sub = np.searchsorted(df_sub['timestamp'], row['timestamp'], side='left', sorter=None)
        for i_s, column in enumerate(columns_to_copy):
            matched_array[i_s].append(df_sub.iloc[index_sub][column])
    # stop warning before copying the found values to df_data
    pd.options.mode.chained_assignment = None
    for index, column in enumerate(columns_to_copy):
        df_data.loc[:, column]= matched_array[index]
    pd.options.mode.chained_assignment = 'warn'

    return df_data

#############################################################################################
# classify rsrp
# input: pandas dataframe with rsrp column
# output: pandas dataframe with extra column containing a five scale rsrp quality indicator
#
#############################################################################################
def classify_rsrp_signal_strength(df):
    conditions = [
        (df['rsrp'] >= -116),
        (df['rsrp'] >= -119) & (df['rsrp'] < -116),
        (df['rsrp'] >= -123) & (df['rsrp'] < -119),
        (df['rsrp'] >= -124) & (df['rsrp'] < -123),
        (df['rsrp'] < -124)
        ]

    values = ['0', '1', '2', '3', '4']
    df['rsrp_quality'] = np.select(conditions, values)
    return df
#############################################################################################
# classify  sinr
# input: pandas dataframe with sinr column
# output: pandas dataframe with extra column containing a four scale sinr quality indicator
#
#############################################################################################
def classify_sinr_signal_strength(df):
    conditions = [
        (df['sinr'] >= 4),
        (df['sinr'] >= 0) & (df['sinr'] < 4),
        (df['sinr'] >= -5) & (df['sinr'] < 0),
        (df['sinr'] < -5)
        ]

    values = ['0', '1', '2', '3']
    df['sinr_quality'] = np.select(conditions, values)
    return df
#############################################################################################
# add five scale color indicator
# input: pandas dataframe with quality indocator column
# output: pandas dataframe with extra column containing a five scale color
#
#############################################################################################
def add_five_color_scale(df, column_to_map, color_column):
    five_color_scale = ['#2ca02c','#d8e305','#fcf260','#fa8f2a','#f50707']

    length_df = df.shape[0]
    i = 0
    tmp_arr = []

    while i < length_df:
        tmp_arr.append(five_color_scale[int(df.iloc[i][column_to_map])])
        i += 1
    tmp_df = pd.DataFrame(
    {
        color_column: tmp_arr
    })
    df = pd.concat([df.reset_index(drop=True), tmp_df.reset_index(drop=True)], axis=1, join='outer')
    return df
#############################################################################################
# combine sinr and rsrp quality indicator
# input: pandas dataframe with sinr - and rsrp quality indocator columns
# output: pandas dataframe with extra column containing a four scale  quality indicator
#
#############################################################################################
def classify_signal_quality(df):
    print(df.shape)
    df = classify_rsrp_signal_strength(df)
    df = classify_sinr_signal_strength(df)
    df['signal_quality_value'] = df[['rsrp_quality','sinr_quality']].max(axis=1).apply(np.int32)
    print(df.shape)
    df = add_five_color_scale(df, 'signal_quality_value', 'signal_quality_color')
    print(df.shape)
    return df
#############################################################################################
# add a five scale quality indicator based on min and max value in a column
# input: pandas dataframe 
# output: pandas dataframe with extra column containing a five scale  quality indicator
#
#############################################################################################
def classify_number_quality(df,column_to_classify,column_to_add ):
    print(df.shape)
    minvalue = df[column_to_classify].min()
    maxvalue = df[column_to_classify].max()
    conditions = [
        (df[column_to_classify] < (maxvalue-minvalue)*1/5),
        (df[column_to_classify] >= (maxvalue-minvalue)*1/5) & (df[column_to_classify] < (maxvalue-minvalue)*2/5),
        (df[column_to_classify] >= (maxvalue-minvalue)*2/5) & (df[column_to_classify] < (maxvalue-minvalue)*3/5),
        (df[column_to_classify] >= (maxvalue-minvalue)*3/5) & (df[column_to_classify] < (maxvalue-minvalue)*4/5),
        (df[column_to_classify] >= (maxvalue-minvalue)*4/5)
        ]

    values = ['4', '3', '2', '1', '0']
    df[column_to_add] = np.select(conditions, values)
    return df
#############################################################################################
# load csv matching file, generated by pcap_analysis
# input: csv filename
# output: pandas dataframe with aggregated per second the dataloss, datarate and data direction
#
#############################################################################################
def read_pcap_analysis_csv(filename):
    df = pd.read_csv(filename)

    df['timestamp_microseconds'] = df['source_pcapPacketHeader.ts_sec'] * 1000000 + df['source_pcapPacketHeader.ts_usec']
    df['timestamp'] = df['timestamp_microseconds'].apply(np.int64)
    df['DateTime'] = pd.to_datetime(df['timestamp'], unit='us')
    df = df.set_index('DateTime')
    # below is a hack to prevent re run of big dataset. We should always use the actual direction per rule
    up_count = df[df['direction'] == 'up'].shape[0]
    down_count = df[df['direction'] == 'down'].shape[0]
    if up_count > down_count:
        direction = 'up'
    else:
        direction = 'down'
    # df_up = df[df['direction'] == 'up']
    # df_down = df[df['direction'] == 'down']
    def aggregate(df_to_aggregate):
        bandwidth_kbps = df_to_aggregate['pcapPacketHeader.orig_len'].sum() * 8 / 1024
        bandwidth_Mbps = bandwidth_kbps / 1024
        packets_lost = df_to_aggregate[df_to_aggregate['lost'] == True].shape[0]
        total_packets = df_to_aggregate.shape[0]
        percentage_lost = packets_lost / total_packets
        # add an hour to align with resource block data
        timestamp = int(df_to_aggregate['timestamp_microseconds'].iloc[0]/1000 + 3600000)
        aggregated_array = {
            'bandwidth_kbps': [bandwidth_kbps],
            'bandwidth_Mbps': [bandwidth_Mbps],
            'packets_lost': [packets_lost],
            'packets_send': [total_packets],
            'percentage_lost': [percentage_lost],
            'timestamp': [timestamp],
            'direction': direction
        }

        return pd.DataFrame.from_dict(aggregated_array)

    df = df.resample('1S').apply(aggregate)

    # do not set index to timestamp else we can not reference it anymore as df['timestamp']
    # df = df.set_index('timestamp')
    # df = df.drop(columns=[ 'DateTime' ])

    return df

#############################################################################################
# main program
#
#
#############################################################################################

# load resource block file from U2020 tool
df_resourceblocks = load_resource_blocks(rb_blocks_file)
print(df_resourceblocks)
averages = {
    "average_up_Mbit_per_second": [],
    "average_down_Mbit_per_second": [],
    "average Uplink Used RB Num": [],
    "average Downlink Used RB Num": [],
    "percentage_lost": [],
    "direction": [],
    "sessionid": [],
    "start_timestamp": []
}

# load data files
index_iperf = 0
index_pcap = 0
for index, file in enumerate(data_files):

    # this operation is very compute intensive, better to first concatenate and then build dataframe:
    print("loading file: " + file)
    filename, file_extension = os.path.splitext(file)
    print("filename: " + filename + " and extension: " + file_extension)
    if file_extension == '.json':
        df_iperf = load_iperf_json(file)
        print(df_iperf)
        df_iperf = merge_dataframes(df_resourceblocks, df_iperf)
        print(df_iperf)
        averages["average_up_Mbit_per_second"].append(df_iperf['up_Mbit_per_second'].mean())
        averages["average_down_Mbit_per_second"].append(df_iperf['down_Mbit_per_second'].mean())
        averages['average Uplink Used RB Num'].append(df_iperf['Uplink Used RB Num'].mean())
        averages['average Downlink Used RB Num'].append(df_iperf['Downlink Used RB Num'].mean())
        averages['percentage_lost'].append(df_iperf.iloc[0]['end.sum.lost_percent'])
        averages['direction'].append(df_iperf.iloc[0]['direction'])
        averages['sessionid'].append(df_iperf.iloc[0]['title'])
        averages['start_timestamp'].append(df_iperf.iloc[0]['timestamp'])

        if index_iperf == 0:
            df_total = df_iperf
        else:
            df_total = df_total.append(df_iperf,ignore_index=False)

        index_iperf = index_iperf + 1
    if file_extension == '.log':
        df_nuttcp = load_nuttcp(file)
        df_iperf = merge_dataframes(df_resourceblocks, df_nuttcp)

        averages["average_up_Mbit_per_second"].append(df_iperf['up_Mbit_per_second'].mean())
        averages["average_down_Mbit_per_second"].append(df_iperf['down_Mbit_per_second'].mean())
        averages['average Uplink Used RB Num'].append(df_iperf['Uplink Used RB Num'].mean())
        averages['average Downlink Used RB Num'].append(df_iperf['Downlink Used RB Num'].mean())
        averages['percentage_lost'].append(df_iperf.iloc[0]['percentage_lost'])
        averages['direction'].append(df_iperf.iloc[0]['direction'])
        averages['sessionid'].append(df_iperf.iloc[0]['title'])
        averages['start_timestamp'].append(df_iperf.iloc[0]['timestamp'])
        if index_iperf == 0:
            df_total = df_iperf
        else:
            df_total = df_total.append(df_iperf,ignore_index=False)
        index_iperf = index_iperf + 1

# print (df_pcap_total)

# create averages dataframe from earlier collected information
df_averages = pd.DataFrame(averages)
print(df_averages)

# sort iperf data based on timestamp
df_total = df_total.sort_values(by=['timestamp'])
# df_pcap_total = df_pcap_total.sort_values(by=['timestamp'])

# sort averages dataframe based on test sequence
df_averages = df_averages.sort_values(by=['start_timestamp'])

# store combined iperf data in single csv file
df_iperf.to_csv('iperftotal.csv')

# store processed file in new csv file (including timestamp)
df_resourceblocks.to_csv('totalresourceblocks.csv')

# store combined dataset in csv file
df_total.to_csv("totaldata.csv")
# df_pcap_total.to_csv("totaldatapcap.csv")
df_averages.to_csv("dfaverages.csv")
# df_total = pd.read_csv("totaldata.csv")
# df_pcap_total = pd.read_csv("totaldatapcap.csv")
# df_averages = pd.read_csv("dfaverages.csv")
# Add minute column, starting by zero for a nice view in a figure
first_timestamp = df_total.iloc[0]['timestamp']
df_total['minutes'] = (df_total['timestamp'] - first_timestamp ) / (1000*60)

# first_timestamp = df_pcap_total.iloc[0]['timestamp']
# df_pcap_total['minutes'] = (df_pcap_total['timestamp'] - first_timestamp ) / (1000*60)
# create figures of data
fig = make_subplots(rows=6, cols=3,
                    shared_xaxes=False,
                    vertical_spacing=0.1, 
                    subplot_titles=("Uplink Used RB Num", "Uplink Used RB Num", "Downlink Used RB Num", "Downlink Used RB Num", "packet loss up", "packet loss down", "uplink Mbps (send data)", "", "", "downlink mbps (received data)", "", "", "lost data"))
if 'Uplink Used RB Num' in df_total:
    fig.add_trace(go.Scatter(x=df_total['minutes'], y=df_total['Uplink Used RB Num'], name="# of RB's per second up"),
                row=1, col=1)
if 'Downlink Used RB Num' in df_total:
    fig.add_trace(go.Scatter(x=df_total['minutes'], y=df_total['Downlink Used RB Num'], name="# of RB's per second down"),
                row=2, col=1)
if 'up_Mbit_per_second' in df_total:
    fig.add_trace(go.Scatter(x=df_total['minutes'], y=df_total['up_Mbit_per_second'], name="Mbps up"),
                row=3, col=1)
if 'down_Mbit_per_second' in df_total:
    fig.add_trace(go.Scatter(x=df_total['minutes'], y=df_total['down_Mbit_per_second'], name="Mbps down"),
                row=4, col=1)
if 'end.sum.lost_percent' in df_total:
    fig.add_trace(go.Scatter(x=df_total['minutes'], y=df_total['end.sum.lost_percent'], name="average percentage lost"),
              row=5, col=1)
if 'percentage_lost' in df_total:
    fig.add_trace(go.Scatter(x=df_total['minutes'], y=df_total['percentage_lost'], name="average percentage lost"),
              row=5, col=1)
if 'sum.lost_percent' in df_total:
    fig.add_trace(go.Scatter(x=df_total['minutes'], y=df_total['sum.lost_percent'], name="percentage lost"),
              row=5, col=1)
# fig.add_trace(go.Scatter(x=df_pcap_total['minutes'], y=df_pcap_total['percentage_lost'], name="percentage lost (pcap)"),
#               row=6, col=1)
fig.add_trace(go.Scatter(x=df_averages.loc[df_averages['direction'] == 'up']['average_up_Mbit_per_second'], 
                         y=df_averages.loc[df_averages['direction'] == 'up']['average Uplink Used RB Num'], 
                         name="average RB's per Mbps up"),
               row=1, col=2)
fig.add_trace(go.Scatter(x=df_averages.loc[df_averages['direction'] == 'down']['average_down_Mbit_per_second'], 
                         y=df_averages.loc[df_averages['direction'] == 'down']['average Downlink Used RB Num'], 
                         name="average RB's per Mbps down"),
               row=1, col=3)
fig.add_trace(go.Scatter(x=df_averages.loc[df_averages['direction'] == 'up']['average_up_Mbit_per_second'], 
                         y=df_averages.loc[df_averages['direction'] == 'up']['percentage_lost'], 
                         name="average percentage lost per mbps up"),
               row=2, col=2)
fig.add_trace(go.Scatter(x=df_averages.loc[df_averages['direction'] == 'down']['average_down_Mbit_per_second'], 
                         y=df_averages.loc[df_averages['direction'] == 'down']['percentage_lost'], 
                         name="average percentage lost per mbps down"),
               row=2, col=3)

# fig.add_trace(go.Scatter(x=df_total['down_Mbit_per_second'], y=df_total['Downlink Used RB Num'], name="# RB's per Mbps down"),
#               row=2, col=3)
fig.update_layout(height=2000, width=2400,
                  title_text="iPerf3 loadtest comparing resource block data, single modem")

fig.update_xaxes(title_text="minutes")
fig.update_xaxes(title_text="Mbps", row=1, col=2)
fig.update_xaxes(title_text="Mbps", row=1, col=3)
fig.update_xaxes(title_text="Mbps", row=2, col=2)
fig.update_xaxes(title_text="Mbps", row=2, col=3)
fig.update_yaxes(title_text="# blocks per second", row=1, col=1)
fig.update_yaxes(title_text="# blocks per second", row=2, col=1)
fig.update_yaxes(title_text="Mbps", row=3, col=1)
fig.update_yaxes(title_text="Mbps", row=4, col=1)
fig.update_yaxes(title_text="perc. lost", row=5, col=1)
fig.show()
