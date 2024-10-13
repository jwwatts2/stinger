# face recognition utility functions using OpenCV and face_recognition on video file

import cv2
import os
import face_recognition
import numpy as np
import time
import hashlib
import pickle
import secrets
import string

debug = False # set to True to display video frames with face rectangles
#MINAREA = 1849 # minimum area of a face in pixels, ignore smaller faces
MINAREA = 2700 # minimum area of a face in pixels, ignore smaller faces

class Face:
    def __init__(self, faceEncoding, frame, location, timestamp):
        self.name = 'Unknown'
        self.encoding = faceEncoding
        self.timestamp = timestamp
        self.frame = frame
        self.location = location

    def save(self, imageDir):
        # use md5 hash of face encoding as filename
        baseFileName = hashFaceEncoding(self.encoding)
        fullFileName = imageDir + baseFileName + '.png'
        cv2.imwrite(fullFileName, self.frame[self.location[0]:self.location[2], 
                                             self.location[3]:self.location[1]])
        # now save the face encoding to a file
        encodingFileName = imageDir + baseFileName + '.enc'
        with open(encodingFileName, 'wb') as f:
            pickle.dump(self.encoding, f)

    def show(self):
        img = self.frame[self.location[0]:self.location[2], self.location[3]:self.location[1]]
        width = self.width() * 2
        height = self.heigth() * 2
        img = cv2.resize(img, (width, height), interpolation = cv2.INTER_AREA)
        cv2.imshow(f'{self.name} {width}x{height}', img)

    def width(self):
        return self.location[1] - self.location[3]
    
    def heigth(self):
        return self.location[2] - self.location[0]

class Employee:
    def __init__(self, name, faceEncoding, status):
        self.name = name
        self.faceEncoding = faceEncoding
        self.status = status

def loadActiveEmployees():
    imageBaseDir = 'C:\\Users\\jwatts\\pythonstuff\\project\\faces\\active\\' # should make this a parameter
    activeEmployees = []
    # descend into subdirectories and load face encodings
    for dir in os.listdir(imageBaseDir):
        if os.path.isdir(imageBaseDir + dir):
            for file in os.listdir(imageBaseDir + dir):
                if file.endswith('.enc'):
                    # might want to limit number of images per employee
                    empEncoding = ''
                    with open(imageBaseDir + dir + '\\' + file, 'rb') as f:
                        empEncoding = pickle.load(f)
                    # might need to remove duplicates
                    activeEmployees.append(Employee(dir, empEncoding, 'active'))
    return activeEmployees

def loadInactiveEmployees():
    imageBaseDir = 'C:\\Users\\jwatts\\pythonstuff\\project\\faces\\inactive\\' # should make this a parameter
    inactiveEmployees = []
    # descend into subdirectories and load face encodings
    for dir in os.listdir(imageBaseDir):
        if os.path.isdir(imageBaseDir + dir):
            for file in os.listdir(imageBaseDir + dir):
                if file.endswith('.enc'):
                    # might want to limit number of images per employee
                    empEncoding = ''
                    # need some error handling here
                    with open(imageBaseDir + dir + '\\' + file, 'rb') as f:
                        empEncoding = pickle.load(f)
                    inactiveEmployees.append(Employee(dir, empEncoding, 'inactive'))
    return inactiveEmployees

def loadFacesToIgnore():
    imageDir = 'C:\\Users\\jwatts\\pythonstuff\\project\\notfaces\\'
    notFaceEncodings = []
    for file in os.listdir(imageDir):
        if file.endswith('.enc'):
            with open(imageDir + file, 'rb') as f:
                faceEncoding = pickle.load(f)
            notFaceEncodings.append(Face(faceEncoding, None, None, None))
    return notFaceEncodings

def displayImage(img):
    scale_percent = 50
    width = int(img.shape[1] * scale_percent / 100)
    height = int(img.shape[0] * scale_percent / 100)
    dim = (width, height)
    img = cv2.resize(img, dim, interpolation = cv2.INTER_AREA)
    cv2.imshow('image', img)

def detectFaces(frame, timestamp, facesToIgnore):
    rgb_img =  cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faceLocs = face_recognition.face_locations(rgb_img)
    faceEncodings = face_recognition.face_encodings(rgb_img, faceLocs, model='small') #large model produces more false positives and false negatives
    faces = []
    for faceLoc, faceEncoding in zip(faceLocs, faceEncodings):
        face = Face(faceEncoding, frame, faceLoc, timestamp)
        if face.heigth() * face.width() > MINAREA:
            found = findClosestFaceMatch(face, facesToIgnore, tolerance=0.5)
            if found is None:
                faces.append(face)
                if debug:
                    cv2.rectangle(frame, (faceLoc[3], faceLoc[0]), (faceLoc[1], faceLoc[2]), (0, 255, 0), 2)
                    displayImage(frame)
            else:
                # this is a face to ignore
                if debug:
                    cv2.rectangle(frame, (faceLoc[3], faceLoc[0]), (faceLoc[1], faceLoc[2]), (0, 0, 255), 2)
                    displayImage(frame)
        else:
            # face is too small 
            if debug:
                cv2.rectangle(frame, (faceLoc[3], faceLoc[0]), (faceLoc[1], faceLoc[2]), (255, 0, 0), 2)
                displayImage(frame)
    return faces

def resizeFrame(img):
    scale_percent = 50
    width = int(img.shape[1] * scale_percent / 100)
    height = int(img.shape[0] * scale_percent / 100)
    img = cv2.resize(img, (width, height), interpolation = cv2.INTER_AREA)
    return img

def findClosestFaceMatch(face, knownFaces, tolerance=0.4):
    knownFaceEncodings = np.array([e.encoding for e in knownFaces])
    minDistance = tolerance
    closestFace = None
    distances = face_recognition.face_distance(knownFaceEncodings, face.encoding)
    for distance, knownFace in zip(distances, knownFaces):
        if distance < minDistance:
            minDistance = distance
            closestFace = knownFace
    return closestFace

def findClosestEmployeeMatch(face, employees, tolerance=0.4):
    knownFaceEncodings = np.array([e.faceEncoding for e in employees])
    minDistance = tolerance
    closestFace = None
    distances = face_recognition.face_distance(knownFaceEncodings, face.encoding)
    for distance, employee in zip(distances, employees):
        if distance < minDistance:
            minDistance = distance
            closestFace = employee
    return closestFace

def getUniqueFaces(faces):
    uniqueFaces = []
    #print (f'uniqueFaces = {uniqueFaces}')
    firstTime = True
    for face in (faces):
        if firstTime:
            # seed with first face
            uniqueFaces.append(face)
            firstTime = False
            continue
        found = findClosestFaceMatch(face, uniqueFaces, tolerance=0.6) # 0.6 seems to work well and is the default anyway
        if found is None:
            uniqueFaces.append(face)
    return uniqueFaces

def identifyFaces(activeEmployees, inactiveEmployees, faces):
    # note that the faces array is modified in place rather than returning a new array
    for face in faces:
        found = findClosestEmployeeMatch(face, activeEmployees, tolerance=0.5)
        if found is None:
            found = findClosestEmployeeMatch(face, inactiveEmployees)
            if found is None:
                face.name = 'Unknown'
            else:
                found.name = found.name + ' (inactive)'
        else:
            face.name = found.name
    return 

def hashFaceEncoding(faceEncoding):
    return hashlib.md5(pickle.dumps(faceEncoding)).hexdigest()

def vprint(verbose, msg, end='\n'):
    if verbose:
        print(msg, end=end)
    
def findFacesInVideo(videoFile, facesToIgnore, verbose=False):
    # convert video to mp4 using ffmpeg
    vprint(verbose, f'converting {videoFile} to mp4')
    # using a random temp file name to avoid collisions
    tempFileName = 'temp'+''.join(secrets.choice(string.digits) for i in range(6))+'.mp4'
    os.system(f'del {tempFileName} > NUL 2>&1')
    startTime = time.time()
    cmd = f'ffmpeg-7.0.2-full_build\\bin\\ffmpeg -i "{videoFile}" {tempFileName} > NUL 2>&1'
    vprint(verbose, f'    cmd = {cmd}...', end='')
    os.system(cmd)
    endTime = time.time()
    if not os.path.exists(tempFileName):
        vprint(verbose, f'Cannot find {tempFileName}')
        exit()
    vprint(verbose, f'done in {endTime - startTime} seconds')

    video = cv2.VideoCapture(tempFileName)
    framesPerSecond = int(video.get(cv2.CAP_PROP_FPS))
    adjustedFramesPerSecond = framesPerSecond
    if framesPerSecond > 15: # could make this a parameter too
        adjustedFramesPerSecond = 15
    totalFrames = video.get(cv2.CAP_PROP_FRAME_COUNT)
    # AXIS Companion video files start 5 seconds before motion starts
    # so we'll skip the first 5 seconds, should make this a parameter
    firstFrameToProcess = adjustedFramesPerSecond*5
    #firstFrameToProcess = adjustedFramesPerSecond*60 # skip the first minute for testing only
    # AXIS Companion video files run for 30 seconds after motion stops
    # so we'll skip the last 30 seconds, should make this a parameter too
    lastFrameToProcess = totalFrames - adjustedFramesPerSecond*30 
    vprint(verbose, msg=f'total frames = {totalFrames}')
    vprint(verbose, msg=f'frames per second = {framesPerSecond}')
    vprint(verbose, msg=f'adjusted frames per second = {adjustedFramesPerSecond}')
    frameCnt = 0
    facesEntireVideo = []
    startTime = time.time()
    vprint(verbose, msg='processing video file...', end='')
    frameCheckRate = adjustedFramesPerSecond # check every second
    originalFrameCheckRate = frameCheckRate
    while True:
        result, frame = video.read()
        if not result:
            break
        vprint(verbose, '.', end='')
        frameCnt += 1
        if frameCnt < firstFrameToProcess:
            continue
        if frameCnt > lastFrameToProcess:
            break
        timestamp = frameCnt / framesPerSecond
        if frameCnt % frameCheckRate == 0: 
            faces = detectFaces(frame, timestamp, facesToIgnore)
            vprint(verbose, msg=f'{len(faces)}', end='')
            if len(faces) > 0:
                for face in faces:
                    facesEntireVideo.append(face)
                # we found at least 1 face, so we'll check more frequently for a bit
                if frameCheckRate > 7:
                    frameCheckRate = frameCheckRate // 2
                else:
                    frameCheckRate = originalFrameCheckRate
            else:
                frameCheckRate = originalFrameCheckRate
        if debug: 
            cv2.imshow('face_recognition test video file', resizeFrame(frame))
            if cv2.waitKey(1) == ord('q'):
                break
    vprint(verbose, 'done')
    endTime = time.time()
    vprint(verbose, f'processed {frameCnt} frames, ({frameCnt/framesPerSecond} s of video) in {endTime - startTime} seconds')  

    video.release()
    cv2.destroyAllWindows()
    os.system(f'del {tempFileName} > NUL 2>&1')
    
    return facesEntireVideo

if __name__ == "__main__":
    logDir = 'C:\\Users\\jwatts\\pythonstuff\\project\\logs\\'

    #target = 'C:\\Users\\jwatts\\Documents\\AXIS Companion - Clips\\ACCC8EA98F27 - 50DD_7-31-2024_7-21-25 AM.asf' # 1 face
    #target = 'C:\\Users\\jwatts\\Documents\\AXIS Companion - Clips\\ACCC8EA98F27 - 50DD_7-31-2024_7-31-45 AM.asf' # 2 faces
    #target = 'C:\\Users\\jwatts\\Documents\\AXIS Companion - Clips\\ACCC8EA98F27 - 50DD_7-31-2024_7-53-28 AM.asf' # 5 faces
    #target = 'C:\\Users\\jwatts\\Documents\\AXIS Companion - Clips\\ACCC8EA98F27 - 50DD_7-31-2024_1-04-06 PM.asf' # 0 face
    # first training run detected more faces than expected
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_1-04-56 PM.asf' 
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_10-12-17 AM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_10-20-25 AM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_11-19-13 AM.asf' # fire alarm
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_11-24-31 AM.asf' # fire alarm
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_11-27-45 AM.asf' 
    # first training run detected less faces than expected
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_10-31-49 AM.asf' 
    # second training run detected more faces than expected after adjusting MINAREA for deduplication
    # target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_12-55-32 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_4-56-40 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_7-55-46 AM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_8-00-21 AM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_9-35-10 AM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_12-32-48 PM.asf'
    # third training run detected more faces than expected after adjusting fps calculation
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_7-46-44 AM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_9-56-22 AM.asf'
    # second training run detected less faces than expected
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_2-55-32 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_3-14-58 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_3-20-44 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_3-46-15 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_5-17-29 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_5-54-14 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_7-34-38 AM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_9-29-58 AM.asf'
    # problems from first recongition run
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_1-28-35 PM.asf' # need more faces for haley, she is looking down
    # this is a good one.  Even matches when subject is wearing sunglasses
    # use for testing recognition time vs database size.  takes 0.01s with 7 faces in database
    # takes 0.001s with new matching algorithm with 199 faces in database
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\ACCC8EA98F27 - 50DD_7-31-2024_1-57-54 PM.asf' 
    # some files from the testing run to expierment with
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\testing\\ACCC8EA98F27 - 50DD_8-12-2024_1-01-17 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\testing\\ACCC8EA98F27 - 50DD_8-12-2024_1-02-43 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\testing\\ACCC8EA98F27 - 50DD_8-12-2024_1-04-00 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\testing\\ACCC8EA98F27 - 50DD_8-12-2024_1-38-20 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\testing\\ACCC8EA98F27 - 50DD_8-12-2024_10-06-51 AM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\testing\\ACCC8EA98F27 - 50DD_8-12-2024_12-30-58 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\testing\\ACCC8EA98F27 - 50DD_8-12-2024_7-52-15 AM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\testing\\ACCC8EA98F27 - 50DD_8-12-2024_1-24-46 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\testing\\ACCC8EA98F27 - 50DD_8-12-2024_1-26-48 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\testing\\ACCC8EA98F27 - 50DD_8-12-2024_12-03-04 PM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\testing\\ACCC8EA98F27 - 50DD_8-12-2024_9-48-27 AM.asf'
    #target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\testing\\ACCC8EA98F27 - 50DD_8-12-2024_1-28-33 PM.asf'
    target = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\testing\\ACCC8EA98F27 - 50DD_8-12-2024_1-10-42 PM.asf'

    startTime = time.time()
    print(f'loading active employees...', end='')
    activeEmployees = loadActiveEmployees()
    endTime = time.time()
    print(f'loaded {len(activeEmployees)} active employees in {endTime - startTime} seconds')
    #print(f'activeEmployeeFaces = {[e.name for e in activeEmployees]}')
    inactiveEmployees = loadInactiveEmployees()
    #print(f'inactiveEmployeeFaces = {[e.name for e in inactiveEmployees]}')
    facesToIgnore = loadFacesToIgnore()
    print(f'loaded {len(facesToIgnore)} "faces" to ignore')
    print(f'processing {target}...', end='')
    startTime = time.time()
    faces = findFacesInVideo(target, facesToIgnore, verbose=True)
    endTime = time.time()
    print(f'found {len(faces)} faces in {endTime - startTime} seconds')
    if debug == True:
        for face in faces:
            face.save(logDir)
            face.show()
            cv2.waitKey(0)

    if len(faces) > 0:
        startTime = time.time()
        print('finding unique faces...', end='')
        uniqueFaces = getUniqueFaces(faces)
        endTime = time.time()
        print(f'found {len(uniqueFaces)} in {endTime - startTime} seconds')
        for uniqueFace in uniqueFaces:
            uniqueFace.save(logDir)
            if debug:
                print(f'face encoding: {hashFaceEncoding(uniqueFace.encoding)}')
        startTime = time.time()
        print('identifying faces...', end='')
        identifyFaces(activeEmployees, inactiveEmployees, uniqueFaces)
        endTime = time.time()
        print(f'completed in {endTime - startTime} seconds')
        print(f'    faces: ')
        for face in uniqueFaces:
            print(f'        {face.name} at {face.timestamp} seconds, area = {face.heigth() * face.width()}')
            if debug:
                face.show()
                cv2.waitKey(0)
    else:
        print('no faces found')