import argparse
import os
import pandas as pd
import facerecogutils as fr
from datetime import datetime
import time
import subprocess
import paramiko
import smtplib
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.mime.multipart import MIMEMultipart

#stinger.py -m investigate -l doorlog08122024.xlsx -v .\videos\testing -o stingerlog.htm
#stinger.py -m monitor -o stinger.log -v .\downloadedvideos

logDir = 'C:\\Users\\jwatts\\pythonstuff\\project\\logs\\'
activeEmployees = []
inactiveEmployees = []
facesToIgnore = []

class EntryEvent:
    def __init__(self, bldg, door, date, time, name):
        self.bldg = bldg
        self.door = door
        self.date = date
        self.time = time
        self.name = name

    def __str__(self):
        return f'{self.bldg} {self.door} {self.date} {self.time} {self.name}'

    def shortName(self):
        return self.name[0] + self.name[1][0]
    
    def timestamp(self):
        ts = None
        if self.date.find('/') > -1:
            ts = datetime.strptime(self.date+' '+self.time, '%m/%d/%Y %I:%M:%S %p')
        else:
            ts = datetime.strptime(self.date+' '+self.time, '%Y-%m-%d %H:%M:%S')
        return ts
    
class DetectionEvent:
    def __init__(self, name, timestamp, source, authorized=False):
        self.name = name
        self.timestamp = timestamp
        self.source = source
        self.authorized = authorized
        self.face = None

def sendEmail(message, subject):
    message = message.replace('\n', '\t\r\n')
    filename = None
    if message.find('See image file') > -1:
        # dig filename out of message
        start = message.find('See image file ') + 15
        end = message.find('.jpg') + 4
        filename = message[start:end]

    msg = MIMEMultipart()
    body = MIMEText(message)
    msg.attach(body)
    stingerEmail = os.environ['STINGER_EMAIL']
    appPassword = os.environ['GMAIL_PASSWORD']
    stingerUserEmail = os.environ['STINGER_USER_EMAIL']
    msg['From'] = stingerEmail
    msg['To'] = stingerUserEmail
    msg['Subject'] = 'Stinger: '+subject
    if filename is not None:
        attachment = open(filename, 'rb')
        att = MIMEBase('application', 'octet-stream')
        att.set_payload(attachment.read())
        encoders.encode_base64(att)
        att.add_header('Content-Disposition', 'attachment', filename='stinger.png')
        msg.attach(att)
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    appPassword = os.environ['GMAIL_PASSWORD']
    s.login(stingerEmail, appPassword)
    s.send_message(msg)
    s.quit()

def sendSMS(message, subject):
    message = message[:100] # only send the first 100 characters of the message
    message = message.replace('\n', '\t\r\n')
    msg = MIMEText(message)
    stingerEmail = os.environ['STINGER_EMAIL']
    appPassword = os.environ['GMAIL_PASSWORD']
    stingerUserSMS = os.environ['STINGER_USER_SMS']
    msg['From'] = stingerEmail
    msg['To'] = stingerUserSMS
    msg['Subject'] = 'Stinger: '+subject
    s = smtplib.SMTP('smtp.gmail.com', 587)
    s.starttls()
    s.login(stingerEmail, appPassword)
    s.send_message(msg)
    s.quit()

def oprint(outputFileName, msg, mode='investigate', end='\n'):
    if outputFileName is None:
        if msg[0] != '<':
            print(msg, end=end)
        return
    if mode == 'monitor':
        if msg[0] != '<':
            logit(outputFileName, msg)
            if msg.find('ALERT:') > -1 or msg.find('ERROR:') > -1:
                sendEmail(msg, 'Alert')
                sendSMS('check email for details', 'Alert')
        return
    # replace leading spaces with &nbsp; so the html file will display correctly
    msg = msg.replace('    ', '&nbsp;&nbsp;&nbsp;&nbsp;')
    # add some color to the output
    fontOn = False
    if msg.find('INFO:') > -1:
        msg = '<font color="green">' + msg
        fontOn = True
    elif msg.find('WARNING:') > -1:
        msg = '<font color="orange">' + msg
        fontOn = True
    elif msg.find('ALERT:') > -1:
        msg = '<font color="red">' + msg
        fontOn = True
    elif msg.find('ERROR:') > -1:
        msg = '<font color="purple">' + msg
        fontOn = True
    with open(outputFileName, 'a') as f:
        if msg == '</p>' or msg == '<p>' or end == '':
            f.write(msg + '\n')
        else:
            f.write(msg + '</br>\n')
        if fontOn:
            f.write('</font>\n')
        f.close()

def getVideoFileName(door, date, time, mode='investigate'):
    cameraLookup = {'South Double Doors': 'ACCC8EA98F27 - 50DD', 
                    'West Double Door': 'ACCC8EA987BC - 92B3', 
                    'East Double Doors': 'ACCC8EA989FF - 50DD'}
    camera = 'unknown'
    try:
        camera = cameraLookup[door]
    except:
        pass
    if mode == 'monitor':
        # change date from yyyy-mm-dd to yyyymmdd
        date = date.replace('-', '')
        # change time from hh:mm:ss P to hhmmss 
        # and add a leading 0 if the hour is less than 10
        # and change PM to 24 hour time
        time = time.split(':')
        hour = time[0]
        if time[1].find('PM') > -1:
            hour = str(int(hour) + 12)
        hour = hour.zfill(2)
        time = hour + time[1][0:2] + time[2][0:2] 
        # need to remove the 50dd from the camera name
        camera = camera.split(' ')[0]
        fileName = camera + '_' + date + '_' + time + '.mkv'
    else:
        fileName = camera + '_' + date.replace('/', '-') + '_' + time.replace(':', '-') + '.asf'
    return fileName

def getTargetVideo(videos, entry, mode='investigate'):
    targetVideoName = getVideoFileName(entry.door, entry.date, entry.time, mode)
    targetCamera = targetVideoName.split('_')[0]
    targetTime = getStartTime(targetVideoName)
    targetVideo = None
    for video in videos:
        camera = video.split('_')[0]
        time = getStartTime(video)
        if camera == targetCamera:
            if time < targetTime:
                targetVideo = video
                break
    return targetVideo
    
def getNextEntryEvent(doorLog, i):
    doorsToMonitor = ['South Double Doors', 'West Double Door', 'East Double Doors']
    eventsToMonitor = ['Access granted', 'Access - door opened']
    while i < len(doorLog):
        row = doorLog.iloc[i]
        event = row['Event']
        if event in eventsToMonitor:
            description = [s.strip() for s in row['Description'].split(',')]
            if len(description) > 3:
                bldg = description[0]
                door = description[1]
                name = description[3].split()
                if bldg == 'Ross Building 1' and door in doorsToMonitor:
                    return i, EntryEvent(bldg, door, row['Date'], row['Time'], name)
        i += 1
    return i, None

def getStartTime(video):
    # the timestamp is between the first _ and the last .
    start = video.find('_') + 1
    end = video.rfind('.')
    ext = video[end+1:]
    dateStr = video[start:end]
    if ext == 'mkv':
        timestamp = datetime.strptime(dateStr, '%Y%m%d_%H%M%S')
    else:
        timestamp = datetime.strptime(dateStr, '%m-%d-%Y_%I-%M-%S %p')
    return timestamp

def imbedImageInReport(outputFileName, videoFileName, timestamp, mode='investigate'):
    # remove extension from video file name
    imgFileName = None
    if videoFileName[0] == '.': # if the video file name has a relative path
        baseVideoFileName = videoFileName.split('.')[1]
        imgFileName = '.\\'+baseVideoFileName+'_'+str(timestamp)+'.jpg'
    else:
        baseVideoFileName = videoFileName.split('.')[0]
        imgFileName = baseVideoFileName+'_'+str(timestamp)+'.jpg'
    if os.path.isfile(imgFileName) == False:
        frame = fr.getFrameFromVideo(videoFileName, timestamp)
        fr.saveFrame(frame, imgFileName)
    oprint(outputFileName, f'<img src="{imgFileName}" alt="{imgFileName}">', mode)

def processVideo(video, videopath, entries, outputFileName, mode='investigate'):
    oprint(outputFileName, f'    processing video: {videopath+'\\'+video}', mode)
    #print(f'        timestamp: {getStartTime(video)}')
    entryNames = [entry.shortName() for entry in entries]
    detections = []
    for entry in entries:
        detections.append(DetectionEvent(entry.shortName(), (entry.timestamp() - getStartTime(video)).total_seconds(), 'door log', True))
    faces = fr.findFacesInVideo(videopath+'\\'+video, facesToIgnore, verbose=False)
    cleanUp = False
    if len(faces) > 0:
        uniqueFaces = fr.getUniqueFaces(faces)
        fr.identifyFaces(activeEmployees, inactiveEmployees, uniqueFaces)
        for face in uniqueFaces:
            authorized = False
            if face.name in entryNames:
                authorized = True
                for detection in detections:
                    if detection.source == 'door log' and detection.name == face.name:
                        detection.face = face
                        break
            faceDetection = DetectionEvent(face.name, face.timestamp, 'camera', authorized)
            faceDetection.face = face
            detections.append(faceDetection)
        detections.sort(key=lambda x: x.timestamp)
        processedNames = []
        unknownMatches = []
        i = 0
        lastAthorized = None
        lastUnauthorized = None
        for detection in detections:
            if detection.name in processedNames:
                continue
            if detection.authorized:
                lastAthorized = detection
                oprint(outputFileName, f'    INFO: Authorized entry by {detection.name} at {int(detection.timestamp)} seconds into the video', mode)
                cleanUp = True
                if detection.face is None and detection.name not in unknownMatches:
                    cleanUp = False
                    oprint(outputFileName, f'    WARNING: face not recognized for entry of {detection.name}', mode)
                    for j in range(len(detections)):
                        if detections[j].name == 'Unknown' and abs(detections[j].timestamp - detection.timestamp) < 12:
                            detections[j].face.save(logDir)
                            imageFileName = logDir+detections[j].face.filename()
                            oprint(outputFileName, f'    ACTION: check {detections[j].face.filename()} for possible match for {detection.name}\n' +
                                                   f'         See image file {imageFileName}.jpg', mode)
                            unknownMatches.append(detection.name)
                            if mode == 'monitor':
                                fr.addFaceToActiveEmployees(detections[j].face, detection.name)
                                oprint(outputFileName, f'         automatically added to employee face data store', mode)
                                oprint(outputFileName, f'         Stinger should be restarted ASAP', mode)
                            break
                if lastUnauthorized is not None and abs(detection.timestamp - lastUnauthorized.timestamp) < 5:
                    cleanUp = False
                    oprint(outputFileName, f'    ALERT: piggybacking detected at {int(lastUnauthorized.timestamp)} seconds into the {video}', mode)
                    if outputFileName is not None:
                        # add screen grab to report
                        imbedImageInReport(outputFileName, videopath+'\\'+video, int(lastUnauthorized.timestamp), mode)
            else:
                if detection.name == 'Unknown':
                    cleanUp = False
                    oprint(outputFileName, f'    WARNING: possible unauthorized entry at {int(detection.timestamp)} seconds into the video', mode)
                    for j in range(len(detections)):
                        if (detections[j].name != 'Unknown' and detections[j].authorized and detections[j].source == 'door log' 
                            and detections[j].name not in unknownMatches and abs(detections[j].timestamp - detection.timestamp) < 12):
                            detection.face.save(logDir)
                            oprint(outputFileName, f'    ACTION: check {detection.face.filename()} for possible match for {detections[j].name}\n' +
                                                   f'         See image file {logDir+detection.face.filename()}.jpg', mode)
                            unknownMatches.append(detections[j].name)
                            break
                else:
                    detection.face.save(logDir)
                    lastUnauthorized = detection
                    cleanUp = False
                    oprint(outputFileName, f'    ALERT: Unauthorized entry by {detection.name}. Check {int(detection.timestamp)} seconds into {video}\n' +
                                           f'         See image file {logDir+detection.face.filename()}.jpg', mode)
                if lastAthorized is not None and abs(detection.timestamp - lastAthorized.timestamp) < 5:
                    cleanUp = False
                    oprint(outputFileName, f'    ALERT: tailgating detected at {int(detection.timestamp)} seconds into the {video}', mode)
                    if outputFileName is not None:
                        # add screen grab to report
                        imbedImageInReport(outputFileName, videopath+'\\'+video, int(detection.timestamp), mode)
            if detection.name != 'Unknown':
                processedNames.append(detection.name)
            i += 1
    else:
        cleanUp = False
        for detection in detections:
            if detection.authorized:
                oprint(outputFileName, f'    INFO: Authorized entry by {detection.name} at {int(detection.timestamp)} seconds into the video', mode)
            oprint(outputFileName, f'    WARNING: no face detected for entry of {detection.name}', mode)
    if cleanUp and mode == 'monitor':
        # clean up the video file
        oprint(outputFileName, f'    INFO: removing video file {videopath}\\{video}', mode)
        os.remove(videopath+'\\'+video)


def investigate(logpath, videopath, outputFileName):
    oprint(outputFileName, '<!DOCTYPE html>', mode='investigate', end='')
    oprint(outputFileName, '<html><body>', mode='investigate', end='')
    oprint(outputFileName, '<head><title>Stinger Investigation Report</title></head>', mode='investigate', end='')
    oprint(outputFileName, 'investigation door log file: ' + logpath)
    oprint(outputFileName, 'investigation video folder: ' + videopath)

    # check if log file exists
    if os.path.isfile(logpath):
        oprint(outputFileName, 'log file exists')
    else:
        oprint(outputFileName, 'log file does not exist')
        return
    #check if video folder exists
    if os.path.isdir(videopath):
        oprint(outputFileName, 'video folder exists')
    else:
        oprint(outputFileName, 'video folder does not exist')
        return
    # load videos file names into list
    videos = []
    for filename in os.listdir(videopath):
        if filename.endswith('.asf'):
            videos.append(filename)
    oprint(outputFileName, f'found {len(videos)} videos in folder')
    # sort videos by timestamp
    videos.sort(key=lambda x: getStartTime(x), reverse=True)
    # read log file
    try:
        doorLog = pd.read_excel(logpath)
    except:
        oprint(outputFileName, 'error reading log file')
        return
    oprint(outputFileName, f'found {len(doorLog)} entries in door log')
    # I known it's not the best practice to load these globals here, but it makes the function calls cleaner
    global activeEmployees
    activeEmployees = fr.loadActiveEmployees()
    oprint(outputFileName, f'loaded {len(activeEmployees)} active employee faces')
    global inactiveEmployees
    inactiveEmployees = fr.loadInactiveEmployees()
    oprint(outputFileName, f'loaded {len(inactiveEmployees)} inactive employee faces')
    global facesToIgnore
    facesToIgnore = fr.loadFacesToIgnore()
    oprint(outputFileName, f'loaded {len(facesToIgnore)} "faces" to ignore')

    entries = []
    processedEntries = []
    i, entry = getNextEntryEvent(doorLog, 0)
    jumpBack = i
    while entry is not None:
        if i not in processedEntries:  # skip any entries we already processed during look ahead
            oprint(outputFileName, '<p>')
            entries.append(entry)
            processedEntries.append(i)
            oprint(outputFileName, f'{entry.door} log indicates entry at {entry.date} {entry.time} by {entry.shortName()}')
            targetVideo = getTargetVideo(videos, entry)
            if targetVideo is None:
                oprint(outputFileName, f'    ERROR: {targetVideo} not found')
            else:
                oprint(outputFileName, f'    {targetVideo} is the most likely video containing the entry')
                # let's look ahead to see if we find any more entries in the door log that might be in the same video
                jumpBack = i
                j = i + 1
                j, lookAheadEntry = getNextEntryEvent(doorLog, j)
                while lookAheadEntry is not None:
                    if j not in processedEntries:
                        nextTargetVideo = getTargetVideo(videos, lookAheadEntry)
                        if lookAheadEntry.door == entry.door: 
                            if nextTargetVideo == targetVideo:
                                oprint(outputFileName, f'        This video will also show entry at {lookAheadEntry.date} {lookAheadEntry.time} by {lookAheadEntry.shortName()}')
                                entries.append(lookAheadEntry)
                                processedEntries.append(j)
                            else:
                                # we're on the same door, but we've moved to a different video
                                break
                    j += 1
                    j, lookAheadEntry = getNextEntryEvent(doorLog, j)
                processVideo(targetVideo, videopath, entries, outputFileName)
                i = jumpBack # now, go back to where we left off before the look ahead
            entries.clear()
            oprint(outputFileName, '</p>')
        i += 1
        i, entry = getNextEntryEvent(doorLog, i)
    oprint(outputFileName, 'investigation complete')
    oprint(outputFileName, '</body></html>', mode='investigate', end='')

def logit(logFileName, msg):
    currentDT = datetime.now()
    with open(logFileName, 'a') as f:
        lines = msg.split('\n')
        for line in lines:
            f.write(f'{currentDT.strftime("%m/%d/%Y %H:%M:%S")}--{line}\n')

def getNewEntries(doorLog, outputFileName):
    logit(outputFileName, 'checking for new door log entries')
    prevDoorLog = doorLog
    hasNewEntries = False
    try:
        doorLog = pd.read_csv("entrapass.csv", names=['Date', 'Time', 'Event', 'Description'])
    except:
        logit(outputFileName, 'no entries csv file found')
        return None, hasNewEntries
    if doorLog.equals(prevDoorLog):
        logit(outputFileName, 'no new entries found')
    else:
        hasNewEntries = True
        if prevDoorLog is None:
            logit(outputFileName, f'found {len(doorLog)} entries in door log')
        else:   
            logit(outputFileName, f'found {len(doorLog)-len(prevDoorLog)} new entries in door log')
    return doorLog, hasNewEntries

def getNewVideos(videos, fullPathMap, outputFileName):
    # Note: fullPathMap is modified in place
    serverInfo = {'192.168.21.10':'ACCC8EA98F27','192.168.21.69':'ACCC8EA989FF','192.168.21.11':'ACCC8EA987BC'}

    hasNewVideos = False
    logit(outputFileName, 'checking for new videos')
    prevVideos = videos
    today = time.strftime('%Y%m%d')
    newVideos = []
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        pwd = os.getenv('AXIS_PASSWORD')

        for ipaddress, camera in serverInfo.items():
            remotePath = f'/mnt/hdd1/recordings/storage_{camera}/{today}'
            ssh.connect(ipaddress, username='root', password=pwd)
            sftp = paramiko.SFTPClient.from_transport(ssh.get_transport())
            for hr in range(24):
                workingPath = remotePath + '/' + str(hr).zfill(2)
                stat = None
                try:
                    stat = sftp.stat(workingPath)
                except FileNotFoundError:
                    pass
                if stat and stat.st_mode == 16893:
                    for dir in sftp.listdir(workingPath):
                        workingPath1 = workingPath + '/' + dir + '/' + today + '_' + str(hr).zfill(2)
                        stat = None
                        try:
                            stat = sftp.stat(workingPath1)
                        except FileNotFoundError:
                            pass
                        if stat and stat.st_mode == 16893:
                            for filename in sftp.listdir(workingPath1):
                                stat = None
                                try:
                                    stat = sftp.stat(workingPath1+'/'+filename)
                                except FileNotFoundError:
                                    pass
                                if stat:
                                    if filename.endswith('.mkv') and stat.st_size > 1000000:
                                        newName = f'{camera}_{filename}'
                                        # video files from the server have a random string after the date
                                        newName = newName[:-9] + '.mkv'
                                        newVideos.append(newName)
                                        fullPathMap[newName] = workingPath1 + '/' + filename
            sftp.close()
            ssh.close()
    except Exception as e:
        logit(outputFileName, f'error getting videos: {e}')
        return [], hasNewVideos
    
    if len(newVideos) == 0:
        logit(outputFileName, 'no videos found')
        return [], hasNewVideos
    
    newVideos.sort(key=lambda x: getStartTime(x), reverse=True)
    if newVideos == prevVideos:
        logit(outputFileName, 'no new videos found')
    else:
        hasNewVideos = True
        if prevVideos is None:
            logit(outputFileName, f'found {len(newVideos)} videos on server')
        else:
            logit(outputFileName, f'found {len(newVideos)-len(prevVideos)} new videos on server')
    return newVideos, hasNewVideos

def downloadVideo(video, fullPathMap, videopath, outputFileName):
    serverInfo = {'ACCC8EA98F27':'192.168.21.10',
                  'ACCC8EA989FF':'192.168.21.69',
                  'ACCC8EA987BC':'192.168.21.11'}

    # check to see if the video is already downloaded
    if os.path.isfile(videopath+'\\'+video):
        logit(outputFileName, f'{video} already downloaded')
        return video
    targetCamera = video.split('_')[0]
    ipaddress = serverInfo[targetCamera]

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    pwd = os.getenv('AXIS_PASSWORD')

    downloadedVideo = None
    try:
        remotePath = fullPathMap[video]
        ssh.connect(ipaddress, username='root', password=pwd)
        sftp = paramiko.SFTPClient.from_transport(ssh.get_transport())
        stat = None
        try:
            stat = sftp.stat(remotePath)
        except FileNotFoundError:
            pass
        if stat:
            logit(outputFileName, f'downloading {video} to {videopath}...')
            sftp.get(remotePath, videopath+'\\'+video) 
            downloadedVideo = video 
        sftp.close()
        ssh.close()
    except Exception as e:
        logit(outputFileName, f'error downloading {video} at {remotePath}: {e}')
        return downloadedVideo
    if downloadedVideo is None:
        logit(outputFileName, f'{video} not found on server')
    else:
        logit(outputFileName, f'{video} downloaded')
    return downloadedVideo

def monitor(videopath, outputFileName):
    logit(outputFileName,'Stinger monitoring started')

    global activeEmployees
    activeEmployees = fr.loadActiveEmployees()
    logit(outputFileName,f'loaded {len(activeEmployees)} active employee faces')
    global inactiveEmployees
    inactiveEmployees = fr.loadInactiveEmployees()
    logit(outputFileName,f'loaded {len(inactiveEmployees)} inactive employee faces')
    global facesToIgnore
    facesToIgnore = fr.loadFacesToIgnore()
    logit(outputFileName,f'loaded {len(facesToIgnore)} "faces" to ignore')

    # run the Entrapass GUI driver in the background
    subprocess.Popen(['python', 'entradriver.py'])
    time.sleep(10)

    # monitor the log file for new entries
    videos = None
    doorLog = None
    fullPathMap = {}
    i = 0
    while True:
        entries = []
        processedEntries = []
        doorLog, hasNewEntries = getNewEntries(doorLog, outputFileName)
        if doorLog is None or hasNewEntries == False:
            time.sleep(30)
            continue
        videos, hasNewVideos = getNewVideos(videos, fullPathMap, outputFileName)
        if videos is None or hasNewVideos == False:
            time.sleep(30)
            continue
        i, entry = getNextEntryEvent(doorLog, i)
        if entry is None:
            logit(outputFileName, 'no relevant door log entries found')
            continue
        jumpBack = i
        while entry is not None:
            if i not in processedEntries:  # skip any entries we already processed during look ahead
                entries.append(entry)
                processedEntries.append(i)
                logit(outputFileName, f'{entry.door} log indicates entry at {entry.date} {entry.time} by {entry.shortName()}')
                time.sleep(30) # wait 30 seconds for the video to be uploaded to the server
                videos, hasNewVideos = getNewVideos(videos, fullPathMap, outputFileName)
                targetVideo = getTargetVideo(videos, entry, mode='monitor')
                if targetVideo is None:
                    start = time.time()
                    while targetVideo is None and time.time() - start < 300: # wait up to 5 minutes for new videos
                        time.sleep(30)
                        videos, hasNewVideos = getNewVideos(videos, fullPathMap, outputFileName)
                        if hasNewVideos:
                            targetVideo = getTargetVideo(videos, entry, mode='monitor')
                if targetVideo is None:
                    logit(outputFileName, f'    ERROR: video not found on server for entry by {entry.shortName()}')
                else:
                    logit(outputFileName, f'    {targetVideo} is the most likely video containing the entry')
                    # let's look ahead to see if we find any more entries in the door log that might be in the same video
                    jumpBack = i
                    j = i + 1
                    start = time.time()
                    hasNewEntries = False
                    while hasNewEntries == False and time.time() - start < 30: # wait up to 30 seconds for new entries
                        time.sleep(10)
                        doorLog, hasNewEntries = getNewEntries(doorLog, outputFileName)
                    j, lookAheadEntry = getNextEntryEvent(doorLog, j)
                    while lookAheadEntry is not None:
                        if j not in processedEntries:
                            videos, hasNewVideos = getNewVideos(videos, fullPathMap, outputFileName)
                            nextTargetVideo = getTargetVideo(videos, lookAheadEntry, mode='monitor')
                            if lookAheadEntry.door == entry.door: 
                                if nextTargetVideo == targetVideo:
                                    logit(outputFileName, f'        This video will also show entry at {lookAheadEntry.date} {lookAheadEntry.time} by {lookAheadEntry.shortName()}')
                                    entries.append(lookAheadEntry)
                                    processedEntries.append(j)
                                else:
                                    # we're on the same door, but we've moved to a different video
                                    break
                        doorLog, hasNewEntries = getNewEntries(doorLog, outputFileName)
                        j += 1
                        j, lookAheadEntry = getNextEntryEvent(doorLog, j)
                    targetVideo = downloadVideo(targetVideo, fullPathMap, videopath, outputFileName)
                    if targetVideo:
                        processVideo(targetVideo, videopath, entries, outputFileName, mode='monitor')
                    else:
                        logit(outputFileName, f'    ERROR: video not found on server for entry by {entry.shortName()}')
                    i = jumpBack # now, go back to where we left off before the look ahead
                entries.clear()
            doorLog, hasNewEntries = getNewEntries(doorLog, outputFileName)
            i += 1
            i, entry = getNextEntryEvent(doorLog, i)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Stinger')
    parser.add_argument('-m', '--mode', type=str, help='investigate or monitor')
    parser.add_argument('-l', '--logpath', type=str, help='full file path to log file to investigate')
    parser.add_argument('-v', '--videopath', type=str, help='full path to folder containing videos to investigate')
    parser.add_argument('-o', '--output', type=str, help='optional output file, otherwise output to console')
    args = parser.parse_args()
    if args.output:
        print('output file: ' + args.output)
        if os.path.isfile(args.output):
            print('output file exists.  overwrite? (y/n)')
            response = input()
            if response.lower() == 'y':
                os.system(f'del {args.output} > NUL 2>&1')
    else:
        print('no output file specified, outputting to console')
    if args.mode == 'investigate':
        if args.logpath and args.videopath:
            investigate(args.logpath, args.videopath, args.output)
        else:
            print('logpath and videopath are required for investigate mode')
            parser.print_help()
    elif args.mode == 'monitor':
        if args.videopath:
            monitor(args.videopath, args.output)
        else:
            print('videopath is required for monitor mode')
            parser.print_help()
    else:
        parser.print_help()