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

# get the password from the environment
pwd = os.getenv('ENTRAPASS')

# launch the app
alreadyRunning = None
try:
    alreadyRunning = Application().connect(path='C:\\Program Files (x86)\\Kantech\\EntraPassWeb\\EntraPass web.exe')    
except:
    pass
if alreadyRunning:
    print('App is already running')
    exit()

app = Application().start('C:\\Program Files (x86)\\Kantech\\EntraPassWeb\\EntraPass web.exe')
time.sleep(5) # give the app time to load

# go to the password field
pwd_x = 745
pwd_y = 690
#pyautogui.moveTo(width+pwd_x, pwd_y, duration=5)
pyautogui.click(pwd_x, pwd_y)
pyautogui.typewrite(pwd)

# go to the login button
login_x = 1150
login_y = 800
#pyautogui.moveTo(width+login_x, login_y, duration=5)
pyautogui.click(login_x, login_y)

time.sleep(5) # give the login time to complete
app.EntraPassweb.minimize()
print('Entrapass is running minimized.  Waiting for network traffic...')

# monitor packet traffic to Entrapass server
sniff(filter="src 52.129.121.116", iface="Ethernet 4", prn=processPacket)