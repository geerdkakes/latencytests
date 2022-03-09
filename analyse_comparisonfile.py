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

# run using: ./analyse_iperfdata.py ../datadir/Low_Latency_Test_Eindhoven_20211129_042742_Eindhoven_BIC_Usage_of_Radio_Resource_Monitoring_20211129_144832.csv ../datadir/20211129_02*/*.json

data_files_1=sys.argv[1]
data_files_2=sys.argv[2]

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
    df['timestamp_milisec'] = df['timestamp_microsec'] / 1000 + 3600000
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
    df['DateTime'] = pd.to_datetime(df['DateTime'],format='%Y-%m-%d %H:%M:%S')

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
    df['timestamp'] = df['timestamp_microseconds'].apply(np.int64) /1000 + 3600000
    df['DateTime'] = pd.to_datetime(df['timestamp'], unit='ms')
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
        bandwidth_received_Mbps = df_to_aggregate[df_to_aggregate['lost'] == False]['pcapPacketHeader.orig_len'].sum() * 8 / (1024 * 1024)
        packets_lost = df_to_aggregate[df_to_aggregate['lost'] == True].shape[0]
        total_packets = df_to_aggregate.shape[0]
        percentage_lost = packets_lost / total_packets * 100
        # add an hour to align with resource block data
        timestamp = int(df_to_aggregate['timestamp_microseconds'].iloc[0]/1000)
        aggregated_array = {
            'bandwidth_kbps': [bandwidth_kbps],
            'bandwidth_Mbps': [bandwidth_Mbps],
            'bandwidth_received_Mbps': [bandwidth_received_Mbps],
            'packets_lost': [packets_lost],
            'packets_send': [total_packets],
            'percentage_lost': [percentage_lost],
            'timestamp': [timestamp],
            'direction': direction
        }

        return pd.DataFrame.from_dict(aggregated_array)

    df_aggregated = df.resample('1S').apply(aggregate)

    # do not set index to timestamp else we can not reference it anymore as df['timestamp']
    # df = df.set_index('timestamp')
    # df = df.drop(columns=[ 'DateTime' ])

    return df, df_aggregated

#############################################################################################
# main program
#
#
#############################################################################################

# load data files
df_pcap_total_1_unag, df_pcap_total_1 = read_pcap_analysis_csv(data_files_1)
df_pcap_total_2_unag, df_pcap_total_2 = read_pcap_analysis_csv(data_files_2)

print (df_pcap_total_1)
print (df_pcap_total_2)





# sort iperf data based on timestamp
df_pcap_total_1 = df_pcap_total_1.sort_values(by=['timestamp'])
df_pcap_total_1_unag = df_pcap_total_1_unag.sort_values(by=['timestamp'])
df_pcap_total_2 = df_pcap_total_2.sort_values(by=['timestamp'])
df_pcap_total_2_unag = df_pcap_total_2_unag.sort_values(by=['timestamp'])

first_timestamp = df_pcap_total_1.iloc[0]['timestamp']
first_timestamp_unag = df_pcap_total_1_unag.iloc[0]['timestamp']
df_pcap_total_1['minutes'] = (df_pcap_total_1['timestamp'] - first_timestamp ) / (1000*60)
df_pcap_total_1_unag['minutes'] = (df_pcap_total_1_unag['timestamp'] - first_timestamp_unag ) / (1000*60)
first_timestamp = df_pcap_total_2.iloc[0]['timestamp']
first_timestamp_unag = df_pcap_total_2_unag.iloc[0]['timestamp']
df_pcap_total_2['minutes'] = (df_pcap_total_2['timestamp'] - first_timestamp ) / (1000*60)
df_pcap_total_2_unag['minutes'] = (df_pcap_total_2_unag['timestamp'] - first_timestamp_unag ) / (1000*60)

# create figures of data
fig = make_subplots(rows=8, cols=1,
                    shared_xaxes=True,
                    vertical_spacing=0.05, 
                    subplot_titles=("downlink mbps (server->dev)", "downlink mbps (server->gnb)", "lost (server->dev)", "lost (server->gnb)", "percentage lost (server->dev)", "percentage lost (server->gnb)", "delay ms (server->dev)", "delay ms (server->gnb)"))
fig.add_trace(go.Scatter(x=df_pcap_total_1['minutes'], y=df_pcap_total_1['bandwidth_received_Mbps'], name="Down bandwidth mbps (pcap)"),
              row=1, col=1)
fig.add_trace(go.Scatter(x=df_pcap_total_1_unag['minutes'], y=df_pcap_total_1_unag['lost'], name="lost"),
              row=3, col=1)
fig.add_trace(go.Scatter(x=df_pcap_total_1['minutes'], y=df_pcap_total_1['percentage_lost'], name="percentage lost (pcap)"),
              row=5, col=1)
fig.add_trace(go.Scatter(x=df_pcap_total_2['minutes'], y=df_pcap_total_2['bandwidth_received_Mbps'], name="Down bandwidth mbps (pcap)"),
              row=2, col=1)
fig.add_trace(go.Scatter(x=df_pcap_total_2_unag['minutes'], y=df_pcap_total_2_unag['lost'], name="lost"),
              row=4, col=1)
fig.add_trace(go.Scatter(x=df_pcap_total_2['minutes'], y=df_pcap_total_2['percentage_lost'], name="percentage lost (pcap)"),
              row=6, col=1)
fig.add_trace(go.Scatter(x=df_pcap_total_1_unag['minutes'], y=df_pcap_total_1_unag['delay_usec']/1000, name="delay ms"),
              row=7, col=1)
fig.add_trace(go.Scatter(x=df_pcap_total_2_unag['minutes'], y=df_pcap_total_2_unag['delay_usec']/1000, name="delay ms"),
              row=8, col=1)
# delay_usec

# fig.add_trace(go.Scatter(x=df_total['down_Mbit_per_second'], y=df_total['Downlink Used RB Num'], name="# RB's per Mbps down"),
#               row=2, col=3)
fig.update_layout(height=2000, width=2400,
                  title_text="iPerf3 loadtest comparing resource block data, single modem")

fig.update_xaxes(title_text="minutes")
fig.update_xaxes(title_text="Mbps", row=1, col=2)
fig.update_xaxes(title_text="Mbps", row=1, col=3)
fig.update_xaxes(title_text="Mbps", row=2, col=2)
fig.update_xaxes(title_text="Mbps", row=2, col=3)
fig.update_yaxes(title_text="packets lost", row=1, col=2)
fig.update_yaxes(title_text="", row=1, col=1)
fig.update_yaxes(title_text="Mbps", row=3, col=1)
fig.update_yaxes(title_text="Mbps", row=4, col=1)
fig.update_yaxes(title_text="perc. lost", row=5, col=1)
fig.update_yaxes(title_text="perc. lost", row=6, col=1)
fig.show()
