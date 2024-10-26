import argparse
import os
import pandas as pd
import facerecogutils as fr
from datetime import datetime

#stinger.py -m investigate -l doorlog08122024.xlsx -v .\videos\testing -o stingerlog.htm
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
        return datetime.strptime(self.date+' '+self.time, '%m/%d/%Y %I:%M:%S %p')
    
class DetectionEvent:
    def __init__(self, name, timestamp, source, authorized=False):
        self.name = name
        self.timestamp = timestamp
        self.source = source
        self.authorized = authorized
        self.face = None

def oprint(outputFileName, msg, end='\n'):
    if outputFileName is None:
        if msg[0] != '<':
            print(msg, end=end)
    else:
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

def getVideoFileName(door, date, time):
    cameraLookup = {'South Double Doors': 'ACCC8EA98F27 - 50DD', 
                    'West Double Door': 'ACCC8EA987BC - 92B3', 
                    'East Double Doors': 'ACCC8EA989FF - 50DD'}
    camera = 'unknown'
    try:
        camera = cameraLookup[door]
    except:
        pass
    return camera + '_' + date.replace('/', '-') + '_' + time.replace(':', '-') + '.asf'

def getTargetVideo(videos, entry):
    targetVideoName = getVideoFileName(entry.door, entry.date, entry.time)
    targetCamera = targetVideoName.split('_')[0]
    targetTime = getStartTime(targetVideoName)
    prevVideo = None
    found = False
    # find the video that is closest to the target time, but not after it
    for video in videos:
        camera = video.split('_')[0]
        time = getStartTime(video)
        if camera == targetCamera and time > targetTime:
            found = True
            break
        prevVideo = video
    if found:
        return prevVideo
    else:
        return None
    
def getNextEntryEvent(doorLog, i):
    doorsToMonitor = ['South Double Doors', 'West Double Door', 'East Double Doors']
    eventsToMonitor = ['Access granted', 'Access - door opened']
    while i < len(doorLog):
        row = doorLog.iloc[i]
        event = row['Event']
        if event in eventsToMonitor:
            description = [s.strip() for s in row['Description'].split(',')]
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
    dateStr = video[start:end]
    return datetime.strptime(dateStr, '%m-%d-%Y_%I-%M-%S %p')

def imbedImageInReport(outputFileName, videoFileName, timestamp):
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
    oprint(outputFileName, f'<img src="{imgFileName}" alt="{imgFileName}">')

def processVideo(video, videopath, entries, outputFileName):
    oprint(outputFileName, f'    processing video: {videopath+'\\'+video}')
    #print(f'        timestamp: {getStartTime(video)}')
    entryNames = [entry.shortName() for entry in entries]
    detections = []
    for entry in entries:
        detections.append(DetectionEvent(entry.shortName(), (entry.timestamp() - getStartTime(video)).total_seconds(), 'door log', True))
    faces = fr.findFacesInVideo(videopath+'\\'+video, facesToIgnore, verbose=False)
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
                oprint(outputFileName, f'    INFO: Authorized entry by {detection.name} at {int(detection.timestamp)} seconds into the video')
                if detection.face is None and detection.name not in unknownMatches:
                    oprint(outputFileName, f'    WARNING: no face detected for entry of {detection.name}')
                    for j in range(len(detections)):
                        if detections[j].name == 'Unknown' and abs(detections[j].timestamp - detection.timestamp) < 10:
                            detections[j].face.save(logDir)
                            oprint(outputFileName, f'    ACTION: check {detections[j].face.filename()} for possible match for {detection.name}')
                            oprint(outputFileName, f'         See image file {logDir+detections[j].face.filename()}.jpg')
                            unknownMatches.append(detection.name)
                            break
                if lastUnauthorized is not None and abs(detection.timestamp - lastUnauthorized.timestamp) < 5:
                    oprint(outputFileName, f'    ALERT: piggybacking detected at {int(lastUnauthorized.timestamp)} seconds into the video')
                    if outputFileName is not None:
                        # add screen grab to report
                        imbedImageInReport(outputFileName, videopath+'\\'+video, int(lastUnauthorized.timestamp))
            else:
                if detection.name == 'Unknown':
                    oprint(outputFileName, f'    WARNING: possible unauthorized entry at {int(detection.timestamp)} seconds into the video')
                    for j in range(len(detections)):
                        if (detections[j].name != 'Unknown' and detections[j].authorized and detections[j].source == 'door log' 
                            and detections[j].name not in unknownMatches and abs(detections[j].timestamp - detection.timestamp) < 10):
                            detection.face.save(logDir)
                            oprint(outputFileName, f'    ACTION: check {detection.face.filename()} for possible match for {detections[j].name}')
                            oprint(outputFileName, f'         See image file {logDir+detection.face.filename()}.jpg')
                            unknownMatches.append(detections[j].name)
                            break
                else:
                    detection.face.save(logDir)
                    lastUnauthorized = detection
                    oprint(outputFileName, f'    ALERT: Unauthorized entry by {detection.name}. Check {int(detection.timestamp)} seconds into video.')
                    oprint(outputFileName, f'         See image file {logDir+detection.face.filename()}.jpg')
                if lastAthorized is not None and abs(detection.timestamp - lastAthorized.timestamp) < 5:
                    oprint(outputFileName, f'    ALERT: tailgating detected at {int(detection.timestamp)} seconds into the video')
                    if outputFileName is not None:
                        # add screen grab to report
                        imbedImageInReport(outputFileName, videopath+'\\'+video, int(detection.timestamp))
            if detection.name != 'Unknown':
                processedNames.append(detection.name)
            i += 1
    else:
        for detection in detections:
            if detection.authorized:
                oprint(outputFileName, f'    INFO: Authorized entry by {detection.name} at {int(detection.timestamp)} seconds into the video')
            oprint(outputFileName, f'    WARNING: no face detected for entry of {detection.name}')


def investigate(logpath, videopath, outputFileName):
    oprint(outputFileName, '<!DOCTYPE html>', end='')
    oprint(outputFileName, '<html><body>', end='')
    oprint(outputFileName, '<head><title>Stinger Investigation Report</title></head>', end='')
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
    videos.sort(key=lambda x: (x.split('_')[0], getStartTime(x)))
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
    # jump ahead for testing
    #i, entry = getNextEntryEvent(doorLog, 75)
    jumpBack = i
    while entry is not None:
        if i not in processedEntries:  # skip any entries we already processed during look ahead
            oprint(outputFileName, '<p>')
            entries.append(entry)
            processedEntries.append(i)
            oprint(outputFileName, f'{entry.door} log indicates entry at {entry.date} {entry.time} by {entry.shortName()}')
            targetVideo = getTargetVideo(videos, entry)
            if targetVideo is None:
                oprint(outputFileName, f'    ERROR: target video not found')
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
        #if i > 115:
        #if i > 45:
            #break
    oprint(outputFileName, 'investigation complete')
    oprint(outputFileName, '</body></html>', end='')



def monitor(outputFileName):
    print('this feature is not yet implemented')

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
        monitor(args.output)
    else:
        parser.print_help()