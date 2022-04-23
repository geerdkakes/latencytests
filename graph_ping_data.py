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
import re
from datetime import datetime
basename = ""

fig_lat = None
interactive_desktop = os.getenv("interactive_desktop", default=None)
data_dir_server = os.getenv("data_dir_server", default=None)
minimum_samples =  int(os.getenv("min_samples", default=1000))
if data_dir_server == None:
    data_dir_server = "."
currentdate = datetime.today().strftime('%Y-%m-%d-%H.%M.%S')


def load_ping_log(filename):
    print("loading file: " + filename)
    fields = ['text']
    df = pd.read_csv(filename, names=fields, skiprows=4)

    df = df[df["text"].str.contains(r'\[([0-9.]*)\]\s([0-9]*)\sbytes\sfrom\s[0-9.]*:\sicmp_seq=([0-9]*)\sttl=[0-9]*\stime=([0-9.]*)\sms')]

    df[["timestamp", "bytes", "sequence_nr", "time"]] = df["text"].str.extract(r'\[([0-9.]*)\]\s([0-9]*)\sbytes\sfrom\s[0-9.]*:\sicmp_seq=([0-9]*)\sttl=[0-9]*\stime=([0-9.]*)\sms')
    df = df.drop(columns=[ 'text'])

    # read file to get start time (should be on first line)
    s = open(filename, 'r')                            
    contents = s.read()     
    title = re.findall(r'title:([a-z0-9_]*)', contents)[0]
    size = re.findall(r'size:([a-z0-9_]*)', contents)[0]
    intervalmsec = re.findall(r'intervalmsec:([a-z0-9_]*)', contents)[0]
    print("title found: " + title)
    df['title'] = title
    df['size'] = size
    df['intervalmsec'] = intervalmsec
    df['timestamp'] = (df['timestamp'].apply(np.float64)*1000).apply(np.int64)
    df['time'] = df['time'].apply(np.float64)
    return df

def prep_directory(basename):
    histogramdir = os.path.join(data_dir_server, "images_histogram", basename+"_ping_"+currentdate)
    try:
        os.makedirs(histogramdir, exist_ok = True)
    except OSError as error:
        print("Directory '%s' can not be created" %histogramdir)
    return histogramdir

def get_xlim(df):
    minimum = np.min(df.iloc[: , -1])
    maximum = np.max(df.iloc[: , -1])
    margin = abs(maximum) * 0.1
    tablename = df.columns[-1]
    print(tablename, minimum, maximum, margin)
    return [minimum - margin,maximum + margin]

def set_legend():
    plt.xticks(fontsize=8)
    plt.legend(fontsize=8,bbox_to_anchor=(1.04,0), loc="lower left", borderaxespad=0)
    plt.tight_layout(rect=[0,0,0.9,1])

filename=sys.argv[1]
for index, filename in enumerate(sys.argv[1:]):
    df = load_ping_log(filename)

    if df.shape[0] < 10:
        print("less than 10 samples. dropping data")
        continue
    title=df.iloc[0]['title']
    basename=title[:11]
    print("basename", basename)
    histogramdir = prep_directory(basename)

    df = df.sort_values(by=['timestamp'])

    first_timestamp = df.iloc[0]['timestamp']
    df['minutes'] = (df['timestamp'] - first_timestamp ) / (1000*60)

    ax = df.plot(x ='minutes', y='time', kind = 'line')
    ax.legend([df.iloc[0]['title']])
    fig1 = ax.get_figure()
    figure_name=histogramdir + '/' +title + '_latency.png'
    print("saving latency data to: " + figure_name)
    fig1.savefig(figure_name)

    if index == 0:
        df_total = df
        df_total[title] = df_total['time']
        df_total = df_total.drop(columns=["timestamp", "bytes", "sequence_nr", "time", "title", "size", "intervalmsec", "minutes"])
    else:
        rows_current=df.shape[0]
        rows_total=df_total.shape[0]
        if rows_current < minimum_samples:
            print("dropping " + title + " only " + str(rows_current) + " samples found")
            continue
        if rows_current > rows_total:
            print("dopping rows from current frame ", rows_total-rows_current)
            df = df.head(rows_total-rows_current)
        elif rows_total > rows_current:
            print("dropping rows from total frame: ", rows_current-rows_total)
            df_total = df_total.head(rows_current-rows_total)

        df_total[title] = df['time']

print(df_total)
print("create histogram figures for " + basename + "...")
# pie1 = df_total.plot.hist(histtype='step',cumulative=True, density=True, rwidth='float',grid=True, bins=500, figsize=[15, 7], xlim=get_xlim(df_total))
pie1 = df_total.plot.hist(histtype='step',cumulative=True, density=True, rwidth='float',grid=True, figsize=[15, 7])
set_legend()
# pie2 = df_total.plot.hist(histtype='step', cumulative=False,rwidth='float',grid=True, bins=500, figsize=[15, 7], xlim=get_xlim(df_total))
pie2 = df_total.plot.hist(histtype='step', cumulative=False,rwidth='float',grid=True, figsize=[15, 7])
set_legend()
fig1 = pie1.get_figure()
fig2 = pie2.get_figure()
fig1.savefig(histogramdir + '/' + basename + '_ping_latency_cum_histogram.png')
fig2.savefig(histogramdir + '/' + basename + '_ping_latency_histogram.png')

df_total.to_csv(histogramdir + '/' +  basename + '_ping_latencies.csv')

print("files stored at: " + histogramdir)




if interactive_desktop:
    plt.show()
