#!/usr/bin/env python3
import pandas as pd
import plotly.express as px
import plotly.io as pio
import csv
import operator
import ntpath
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
from plotly.subplots import make_subplots
from plotly import graph_objs as go, io as pio, tools
from datetime import datetime
basename = ""

fig_lat = None
interactive_desktop = os.getenv("interactive_desktop", default=None)
data_dir_server = os.getenv("data_dir_server", default=None)
minimum_samples =  int(os.getenv("min_samples", default=1000))

print("using minimal samples: " + str(minimum_samples))


if len(sys.argv) < 3:
    print("specify filename(s) to analysis: " + sys.argv[0] + " tcp:udp <filename1>:description <filename2>:description ")

files_to_analyse=[]
protocols=sys.argv[1].split(":")

for index, element in enumerate(sys.argv[2:]):
    argarr = element.split(":")
    filedict = {}
    filedict['filename'] = argarr[0]
    filedict['description'] = argarr[1]
    if basename == "":
        basename = argarr[1][:11]
        print("set basename to: " + basename)
    files_to_analyse.append(filedict)

if data_dir_server == None:
    data_dir_server = "."
currentdate = datetime.today().strftime('%Y-%m-%d-%H.%M.%S')
histogramdir = os.path.join(data_dir_server, "images_histogram", basename+"_"+currentdate)
try:
    os.makedirs(histogramdir, exist_ok = True)
    print("Directory '%s' created successfully" %histogramdir)
except OSError as error:
    print("Directory '%s' can not be created" %histogramdir)


infofile = histogramdir + '/infofile.txt'
print("storing al statistics in '%s'" %infofile)
infofile_handler = open(infofile,"w")
infofile_handler.write("protocols: " + sys.argv[1] +'\n')
infofile_handler.write("testruns: " + sys.argv[2] +'\n')
variables = []

for protocol in protocols:
    if protocol == "udp":
        # variables.append([None,51000,"udp_up","up","udp"])
        # variables.append([51000,None,"udp_down","down","udp"])
        # variables.append([None,51001,"udp_up","up","udp"])
        # variables.append([51001,None,"udp_down","down","udp"])
        variables.append([None,None,"udp_up","up","udp"])
        variables.append([None,None,"udp_down","down","udp"])
    if protocol == "tcp":
        variables.append([None,1883,"mqtt_up","up","tcp"])
        variables.append([1883,None,"mqtt_down","down","tcp"])

len_vars = len(variables)
len_files = len(files_to_analyse)
nr_graphs = len_files*len_vars
titels = np.empty(nr_graphs, dtype=object)
for var_index, var in enumerate(variables):
    for file_index, file in  enumerate(files_to_analyse):
        graph_index=file_index*len_vars+var_index
        titels[graph_index] = var[2] + '_' + file['description']
        print(titels[graph_index])

print("analysing protocols:", protocols)

# 0 source_packetNr,214019
# 1 destination_packetNr,43
# 2 source_pcapPacketHeader.ts_sec,1617178783
# 3 source_pcapPacketHeader.ts_usec,974938
# 4 destination_pcapPacketHeader.ts_sec,1617178783
# 5 destination_pcapPacketHeader.ts_usec,988770
# 6 delay_usec,13832
# 7 pcapPacketHeader.orig_len,104
# 8 udpHeader.dest_port,5001
# 9 udpHeader.src_port,52688
# 10 tcpHeader.dest_port
# 11 tcpHeader.src_port
# 12 protocol,udp
# 13 direction,up
# 14 lost, false
#
# calculate interpackettime (ts_sec(t=2)2*1000000+ts_usec(t=2))-(ts_sec(t=2)2*1000000+ts_usec(t=2))
def path_leaf(path):
    head, tail = ntpath.split(path)
    return tail or ntpath.basename(head)
def read_latency(sourceport, destport, basename, direction, filename, protocol):
    with open(filename) as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        dates1 = []
        latencies1 = []
        lost1 = []
        pcktlength = []
        source_interpackettimes1 = []
        destination_interpackettimes1 = []
        firsttimestamp = 0
        last_dest_usec = 0
        last_src_usec = 0
        print("reading file: " + filename)
        print("running with protol: " + protocol + " sourceport " + str(sourceport) + " destport: " + str(destport) + " direction: " + direction)
        for index, row in enumerate(readCSV):
            if (index == 1):
                firsttimestamp = float(row[2])*1000000+float(row[3])
            if index == 0 or row[0] == 'source_packetNr':
                continue
            if protocol == None or row[12] != protocol:
                continue
            if direction == None or row[13] != direction:
                continue
            date = (float(row[2])*1000000+float(row[3]) - firsttimestamp)/1000000
            pcktlength.append(int(row[7]))
            if row[14] == "true":
                lost1.append(0)
                dates1.append(date)
                latencies1.append(None)
            else:
                if last_dest_usec == 0:
                    last_dest_usec = int(row[4])*1000000+int(row[5])
                    last_src_usec = int(row[2])*1000000+int(row[3])
                else:
                    current_dest_usec = int(row[4])*1000000+int(row[5])
                    current_src_usec = int(row[2])*1000000+int(row[3])
                    source_interpackettime = (current_src_usec - last_src_usec)/1000
                    destination_interpackettime = (current_dest_usec - last_dest_usec)/1000
                    last_src_usec = current_src_usec
                    last_dest_usec = current_dest_usec
                    # check possible negative values because of merging different timeframes
                    if source_interpackettime >= 0 and destination_interpackettime >=0 and source_interpackettime < 10000 and destination_interpackettime < 10000:
                        destination_interpackettimes1.append(destination_interpackettime)
                        source_interpackettimes1.append(source_interpackettime)
                latency = float(row[6]) / 1000
                dates1.append(date)
                latencies1.append(latency)
                lost1.append(None)
        return {
                    'timeline': dates1,
                    'latencies':  latencies1,
                    'source_interpackettimes': source_interpackettimes1,
                    'destination_interpackettimes': destination_interpackettimes1,
                    'losts': lost1,
                    'packetsize': pcktlength,
                    'basename': basename,
                    'filename': filename,
                    'sourceport': sourceport,
                    'destport': destport,
                    'direction': direction,
                    'protocol': protocol
                }

# [source, destination, basename, direction]
def calc_perc_lat(latencies_arr, perc):
    latencies_sorted = np.sort(latencies_arr)
    latencies_99_pos = int(len(latencies_arr) *perc)
    return latencies_sorted[latencies_99_pos]

def set_legend():
    plt.xticks(fontsize=8)
    plt.legend(fontsize=8,bbox_to_anchor=(1.04,0), loc="lower left", borderaxespad=0)
    plt.tight_layout(rect=[0,0,0.9,1])

def get_xlim(df):
    minimum = np.min(df.iloc[: , -1])
    maximum = np.max(df.iloc[: , -1])
    margin = abs(maximum) * 0.1
    tablename = df.columns[-1]
    print(tablename, minimum, maximum, margin)
    return [minimum - margin,maximum + margin]

def save_image(figure, filepath):
    print("saving pio graphs...")
    # disable mathjax to prevent large timeouts trying to do internet call
    pio.kaleido.scope.mathjax = None
    try:
        print("...html...")
        pio.write_html(figure, filepath + '.html')
        # don't write png file. takes to much time
        # print("...png...")
        # pio.write_image(fig=figure, format="png", file=filepath+".png", engine="kaleido")
        print("finished writing files")
    except Exception as e:
        print("Could not write figure to file: ", filepath,e)

lat_analysis = []
for pars_index, pars in enumerate(variables):
    minlen = None
    lat_analysis_files = []
    max_latency=0
    for file_to_anayse in files_to_analyse:
        #sourceport, destport, basename, direction, filename, protocol
        basename=pars[2] + '_' + file_to_anayse['description']
        read_lat_result = read_latency(pars[0], pars[1], basename, pars[3],file_to_anayse['filename'], pars[4])
        lat_analysis_files.append(read_lat_result)
        length_arr = len(read_lat_result['latencies'])
        lengt_arr_interp = len(read_lat_result['source_interpackettimes'])
        if minlen == None and length_arr >= minimum_samples:
            minlen = length_arr
            min_interp_len = lengt_arr_interp
        else:
            if length_arr >= minimum_samples:
                minlen = min(length_arr, minlen)
                min_interp_len = min(min_interp_len,lengt_arr_interp)
    lat_data_for_frame = {}
    timeline_for_frame = {}
    lost_packets_for_frame = {}
    source_interp_data_for_frame = {}
    destination_interp_data_for_frame = {}
    pcktsize_data_for_frames = {}
    for lat_data in lat_analysis_files:
        if len(lat_data['latencies']) < minimum_samples:
            continue
        print("analysing: " +lat_data['basename'] )
        lat_data_for_frame[lat_data['basename']+'_latency'] = lat_data['latencies'][:minlen]
        lost_packets_for_frame[lat_data['basename']+'_latency'] = lat_data['losts'][:minlen]
        timeline_for_frame[lat_data['basename']+'_latency'] = lat_data['timeline'][:minlen]
        source_interp_data_for_frame[lat_data['basename']+'_src_interpcktime'] = lat_data['source_interpackettimes'][:min_interp_len]
        destination_interp_data_for_frame[lat_data['basename']+'_dst_interpcktime'] = lat_data['destination_interpackettimes'][:min_interp_len]
        pcktsize_data_for_frames[lat_data['basename']+'_packetsize'] = lat_data['packetsize'][:minlen]
        np_latency_arr = np.array(lat_data['latencies'], dtype=np.float64)
        lat_data_max_lat = np.round(np.nanmax(np_latency_arr),1,out=None)
        max_latency=max(lat_data_max_lat,max_latency)
        lostpackets=np.count_nonzero(lat_data['losts']==0)
        packetloss=lostpackets/len(lat_data['losts'])
        print(lat_data['basename']+'_latency', minlen, max_latency)
        infofile_handler.write(lat_data['basename']+'_min_latency: ' + str(np.round(np.min(np_latency_arr),1,out=None))+'\n')
        infofile_handler.write(lat_data['basename']+'_mean_latency: ' + str(np.round(np.mean(np_latency_arr),1,out=None))+'\n')
        infofile_handler.write(lat_data['basename']+'_std_latency: ' + str(np.round(np.std(np_latency_arr),1,out=None))+'\n')
        infofile_handler.write(lat_data['basename']+'_95th_percentile_latency: ' + str(calc_perc_lat(np_latency_arr, 0.95))+'\n')
        infofile_handler.write(lat_data['basename']+'_99th_percentile_latency: ' + str(calc_perc_lat(np_latency_arr, 0.99))+'\n')
        infofile_handler.write(lat_data['basename']+'_max_latency: '+ str(lat_data_max_lat)+'\n')
        infofile_handler.write(lat_data['basename']+'_mean_source_interpackettime: ' + str(np.round(np.mean(lat_data['source_interpackettimes']),1,out=None))+'\n')
        infofile_handler.write(lat_data['basename']+'_std_source_interpackettime: ' + str(np.round(np.std(lat_data['source_interpackettimes']),1,out=None))+'\n')
        infofile_handler.write(lat_data['basename']+'_mean_dest_interpackettime: ' + str(np.round(np.mean(lat_data['destination_interpackettimes']),1,out=None))+'\n')
        infofile_handler.write(lat_data['basename']+'_std_dest_interpackettime: ' + str(np.round(np.std(lat_data['destination_interpackettimes']),1,out=None))+'\n')
        infofile_handler.write(lat_data['basename']+'_lostpacketcount: ' + str(lostpackets)+'\n')
        infofile_handler.write(lat_data['basename']+'_lostpacketperc: ' + str(packetloss)+'\n')
        infofile_handler.write(lat_data['basename']+'_direction: ' + lat_data['direction']+'\n')
        infofile_handler.write(lat_data['basename']+'_mean_packet_size ' + str(np.round(np.mean(lat_data['packetsize']),1,out=None))+'\n')

    lat_analysis.append(lat_analysis_files)
    df_lat = pd.DataFrame(lat_data_for_frame)
    df_timeline = pd.DataFrame(timeline_for_frame)
    df_interp_src = pd.DataFrame(source_interp_data_for_frame)
    df_interp_dst = pd.DataFrame(destination_interp_data_for_frame)
    df_size = pd.DataFrame(pcktsize_data_for_frames)
    df_lost = pd.DataFrame(lost_packets_for_frame)

    # docs: https://yiyibooks.cn/meikunyuan6/pandas/pandas/generated/pandas.DataFrame.plot.html#pandas.DataFrame.plot
    print("create histogram figures for " + pars[2] + "...")
    pie1 = df_lat.plot.hist(histtype='step',cumulative=True, density=True, rwidth='float',grid=True, bins=500, figsize=[15, 7], xlim=get_xlim(df_lat))
    set_legend()
    pie2 = df_lat.plot.hist(histtype='step', cumulative=False,rwidth='float',grid=True, bins=500, figsize=[15, 7], xlim=get_xlim(df_lat))
    set_legend()
    pie3 = df_interp_src.plot.hist(histtype='step', cumulative=False,rwidth='float',grid=True, bins=500,  figsize=[15, 7], xlim=get_xlim(df_interp_src))
    set_legend()
    pie4 = df_interp_dst.plot.hist(histtype='step', cumulative=False,rwidth='float',grid=True, bins=500, figsize=[15, 7], xlim=get_xlim(df_interp_dst))
    set_legend()
    fig1 = pie1.get_figure()
    fig2 = pie2.get_figure()
    fig3 = pie3.get_figure()
    fig4 = pie4.get_figure()
    fig1.savefig(histogramdir + '/' + pars[2] + '_latency_cum_histogram.png')
    fig2.savefig(histogramdir + '/' + pars[2] + '_latency_histogram.png')
    fig3.savefig(histogramdir + '/' + pars[2] + '_src-interpackettime.png')
    fig4.savefig(histogramdir + '/' +  pars[2] + '_dst-interpackettime.png')
    df_lat.to_csv(histogramdir + '/' +  pars[2] + '_latencies.csv')
    df_interp_src.to_csv(histogramdir + '/' +  pars[2] + '_src-interpackettime.csv')
    df_interp_dst.to_csv(histogramdir + '/' +  pars[2] + '_dst-interpackettime.csv')

    for column in df_lat:
        if column in df_timeline:
            pd.DataFrame(dict(time=df_timeline[column], latency=df_lat[column])).to_csv(histogramdir + '/' +  'latency' + column + '.csv')
    if fig_lat is None:
        nr_graphs = df_lat.shape[1]*len_vars
        print("create latency figures... ")
        fig_lat = make_subplots(rows=nr_graphs, cols=1,
                        shared_xaxes=False,
                        vertical_spacing=0.01,
                        subplot_titles=titels)
    for index, column in enumerate(df_lat):
        row = index*len_vars+pars_index+1

        fig_lat.add_trace(go.Scatter( y=df_lat[column], 
                                      x=df_timeline[column],
                                      name=column),
                                      row=row, 
                                      col=1)
        fig_lat.add_trace(go.Scatter( y=df_lat[column],
                                      x=df_timeline[column], 
                                      name=column, 
                                      mode='markers',
                                      marker=dict(
                                        size=3,
                                        color='MediumPurple'
                                      ),
                                      showlegend=False
                                    ),row=row, col=1 )
        fig_lat.add_trace(go.Scatter( y=df_lost[column],
                                      x=df_timeline[column],
                                      name=column, 
                                      mode='markers',
                                      marker_symbol=17,
                                      marker=dict(
                                        size=5,
                                        color='rgba(241, 50, 14, 1)'
                                      ),
                                      showlegend=False
                                    ),row=row, col=1 )
        fig_lat.update_yaxes(title_text="latency (ms)",
                                      fixedrange=True,
                                      range=[0, 40],
                                      ticktext=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30, 35, 40],
                                      tickvals=[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 25, 30, 35, 40],
                                      tickmode="array",
                                      titlefont=dict(size=10),
                                      row=row,
                                      col=1 )
    fig_lat.update_layout(height=10000, width=9600,
                            title_text="latency")

if interactive_desktop:
    print("generating interactie latency graph...")
    fig_lat.show()

save_image(fig_lat, histogramdir + '/' + 'lantency_graph')
if interactive_desktop:
    print("generating interactive history graphs......")
    plt.show()
    # fig = px.line(df, x = 'timestamp', y = 'latency', title=path_leaf(filename))
infofile_handler.close()
print("stored files in: " + histogramdir)
print("to zip:")
print("cd " + os.path.join(data_dir_server, "images_histogram") + "; zip -r " + currentdate + ".zip " + currentdate + "/*")
