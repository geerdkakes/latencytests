# latencytests


This repository contains tools to automate latency tests. Besides this repository you will also need:

on all test systems:
- tcpdump
- https://github.com/geerdkakes/ServerSocketTCP_UDP

on the device if testing with mqtt:
- https://github.com/geerdkakes/mqtt-delay

on the server:
- https://github.com/geerdkakes/pcap-analysis


## before testing

Setup all programs and create a file variables.sh (using the variables.sh.skel). Create your first testcase.csv file defining your testruns, using the file sampletest.csv as an example.
