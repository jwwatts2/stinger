# scapy test
from scapy.all import *
import re 

payloadData = ''
rec = ''
parseStep = 0

def buildAccessRecord(start, end):
    global payloadData
    global rec
    global parseStep

    datePattern = r'^\d{4}-\d{2}-\d{2}.*'
    # if array starts with a date
    if re.match(datePattern, payloadData):
        # remove the double spaces
        payloadData = re.sub(r'\s\s', '","', payloadData)
        if parseStep == 1:
            rec = '"'+payloadData+'",'
        else:
            parseStep = 0
    if parseStep == 2:
        rec += '"'+payloadData+'",'
    if parseStep == 15:
        rec += '"'+payloadData+','
    if parseStep == 18:
        rec += payloadData+'"'
        print(f'record={rec}')
        parseStep = 0
        rec = ''

def print_pkt(pkt, live=True):
    global payloadData
    global rec
    global parseStep
    if live == False or TCP in pkt:
        #print(f"SRC: {pkt[IP].src} -> DST: {pkt[IP].dst} | {pkt[TCP].sport} -> {pkt[TCP].dport}")
        #print(f"Payload: {bytes(pkt[TCP].payload)}")
        if live:
            payload = bytes(pkt[TCP].payload).decode('utf-8', 'ignore')
            #print(f'Payload: {payload}')
        else:
            payload = pkt
        # log the payload
        if live:
            with open('payload.txt', 'a') as f:
                f.write(str(payload))
        found = True
        end = 0
        while found:
            start = payload.find('<Value>', end)
            end = payload.find('</Value>', end)
            #print(f'Start: {start} | End: {end}')
            if end > -1:
                end += 8
                if start > -1:
                    if end > start:
                        #print(array)
                        parseStep += 1
                        buildAccessRecord(start, end)
                        payloadData = payload[start+7:end-8]
                    else:
                        payloadData += str(payload[:end-8])
                        #print(array)
                        parseStep += 1
                        buildAccessRecord(start, end)
                        payloadData = payload[start+7:]
                else:
                    payloadData += payload[:end-8]
            else:
                if start > -1:
                    #print(array)
                    parseStep += 1
                    buildAccessRecord(start, end)
                    payloadData = payload[start+7:]
                else:
                    found = False

liveMode = True

if liveMode:
    sniff(filter="src 52.129.121.116", iface="Ethernet 4", prn=print_pkt)
else:
    # read from a payload file
    with open('payload.txt', 'r') as f:
        for line in f:
            print_pkt(line, False)