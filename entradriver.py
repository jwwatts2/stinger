# second attempt at controlling the entrapass app
from pywinauto.application import Application
import pyautogui
import time
import os
from scapy.all import *
import re 

payloadData = ''
rec = ''
parseStep = 0
recCnt = 0

def logit(msg):
    currentDT = datetime.now()
    with open('entrapass.log', 'a') as f:
        f.write(f'{currentDT.strftime("%m/%d/%Y %H:%M:%S")}--{msg}\n')

def buildAccessRecord(start, end):
    global payloadData
    global rec
    global parseStep
    global recCnt

    datePattern = r'^\d{4}-\d{2}-\d{2}.*'
    # if packet payload starts with a date
    if re.match(datePattern, payloadData):
        # remove the double spaces
        payloadData = re.sub(r'\s\s', '","', payloadData)
        if parseStep == 1:
            rec = '"'+payloadData+'",'
        else:
            parseStep = 0
            rec = ''
    if parseStep == 2:
        rec += '"'+payloadData+'",'
    if parseStep == 15:
        rec += '"'+payloadData+','
    if parseStep == 18:
        rec += payloadData+'"'
        recCnt += 1
        logit(f'{recCnt},{rec}')
        with open('entrapass.csv', 'a') as f:
            f.write(f'{rec}\n')
        parseStep = 0
        rec = ''

def processPacket(pkt):
    global payloadData
    global rec
    global parseStep
    if TCP in pkt:
        payload = bytes(pkt[TCP].payload).decode('utf-8', 'ignore')
        found = True
        end = 0
        while found:
            start = payload.find('<Value>', end)
            end = payload.find('</Value>', end)
            if end > -1:
                end += 8
                if start > -1:
                    if end > start:
                        parseStep += 1
                        buildAccessRecord(start, end)
                        payloadData = payload[start+7:end-8]
                    else:
                        payloadData += str(payload[:end-8])
                        parseStep += 1
                        buildAccessRecord(start, end)
                        payloadData = payload[start+7:]
                else:
                    payloadData += payload[:end-8]
            else:
                if start > -1:
                    parseStep += 1
                    buildAccessRecord(start, end)
                    payloadData = payload[start+7:]
                else:
                    found = False

# get the password from the environment
pwd = os.getenv('ENTRAPASS')

# delete the log file
if os.path.exists('entrapass.log'):
    os.remove('entrapass.log')
logit('Starting Entrapass driver')

# delete the csv file
if os.path.exists('entrapass.csv'):
    os.remove('entrapass.csv')

# launch the app
alreadyRunning = None
try:
    alreadyRunning = Application().connect(path='C:\\Program Files (x86)\\Kantech\\EntraPassWeb\\EntraPass web.exe')    
except:
    pass
if alreadyRunning:
    logit('Entrapass Web is already running. Stopping it...')  
    alreadyRunning.kill()

logit('Starting Entrapass Web...')
app = Application().start('C:\\Program Files (x86)\\Kantech\\EntraPassWeb\\EntraPass web.exe')
time.sleep(5) # give the app time to load

debug = False
if debug:
    pwd_x = 786
    pwd_y = 554
    login_x = 1110
    login_y = 640
    event_x = 126
    event_y = 105
else:
    pwd_x = 745
    pwd_y = 690
    login_x = 1150
    login_y = 800
    event_x = 128
    event_y = 125

# go to the password field
pyautogui.click(pwd_x, pwd_y)
pyautogui.typewrite(pwd)

# go to the login button
pyautogui.click(login_x, login_y)
time.sleep(2) # give the login time to complete

# go to the events tab
pyautogui.click(event_x, event_y)
time.sleep(2) # give the events page time to load

app.EntraPassweb.minimize()
logit('Entrapass Web is running minimized.  Waiting for network traffic...')

# monitor packet traffic to Entrapass server
try:
    sniff(filter="src 52.129.121.116", iface="Ethernet 4", prn=processPacket)
except:
    sniff(filter="src 52.129.121.116", iface="Wi-Fi", prn=processPacket)