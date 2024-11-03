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
        fullFileName = imageDir + self.filename() + '.jpg'
        cv2.imwrite(fullFileName, self.frame[self.location[0]:self.location[2], 
                                             self.location[3]:self.location[1]])
        # now save the face encoding to a file
        encodingFileName = imageDir + self.filename() + '.enc'
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
    
    def filename(self):
        return hashFaceEncoding(self.encoding)

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
                    empEncoding = ''
                    with open(imageBaseDir + dir + '\\' + file, 'rb') as f:
                        empEncoding = pickle.load(f)
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
                    empEncoding = ''
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
    faceDetected = False
    for faceLoc, faceEncoding in zip(faceLocs, faceEncodings):
        face = Face(faceEncoding, frame, faceLoc, timestamp)
        faceDetected = True
        if face.heigth() * face.width() >= MINAREA:
            found = findClosestFaceMatch(face, facesToIgnore, tolerance=0.5)
            if found is None:
                faces.append(face)
                if debug:
                    cv2.rectangle(frame, (faceLoc[3], faceLoc[0]), (faceLoc[1], faceLoc[2]), (0, 255, 0), 2)
                    displayImage(frame)
            else:
                # this is a face to ignore
                faceDetected = False
                if debug:
                    cv2.rectangle(frame, (faceLoc[3], faceLoc[0]), (faceLoc[1], faceLoc[2]), (0, 0, 255), 2)
                    displayImage(frame)
        else:
            # face is too small 
            if debug:
                cv2.rectangle(frame, (faceLoc[3], faceLoc[0]), (faceLoc[1], faceLoc[2]), (255, 0, 0), 2)
                displayImage(frame)
    return faces, faceDetected

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

def getFrameFromVideo(videoFile, timestamp):
    tempFileName = 'temp'+''.join(secrets.choice(string.digits) for i in range(6))+'.mp4'
    os.system(f'del {tempFileName} > NUL 2>&1')
    cmd = f'ffmpeg-7.0.2-full_build\\bin\\ffmpeg -i "{videoFile}" {tempFileName} > NUL 2>&1'
    os.system(cmd)
    video = cv2.VideoCapture(tempFileName)
    framesPerSecond = int(video.get(cv2.CAP_PROP_FPS))
    frameNumber = int(timestamp * framesPerSecond)
    video.set(cv2.CAP_PROP_POS_FRAMES, frameNumber)
    result, frame = video.read()
    video.release()
    return frame

def saveFrame(frame, filename):
    cv2.imwrite(filename, resizeFrame(resizeFrame(frame)))    
    
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
        return []
    vprint(verbose, f'done in {endTime - startTime} seconds')

    video = cv2.VideoCapture(tempFileName)
    framesPerSecond = int(video.get(cv2.CAP_PROP_FPS))
    adjustedFramesPerSecond = framesPerSecond
    if framesPerSecond > 15: # could make this a parameter too
        adjustedFramesPerSecond = 15
    totalFrames = video.get(cv2.CAP_PROP_FRAME_COUNT)
    firstFrameToProcess = 1
    lastFrameToProcess = totalFrames
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
            faces, faceDetected = detectFaces(frame, timestamp, facesToIgnore)
            vprint(verbose, msg=f'{len(faces)}', end='')
            if faceDetected:
                for face in faces:
                    facesEntireVideo.append(face)
                # we found at least 1 face, so we'll check more frequently for a bit
                frameCheckRate = 1
            if frameCheckRate < originalFrameCheckRate:
                frameCheckRate += 1
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

def addFaceToActiveEmployees(face, name):
    imageDir = 'C:\\Users\\jwatts\\pythonstuff\\project\\faces\\active\\' # should make this a parameter
    imageDir = imageDir + name + '\\'
    # create directory if it doesn't exist
    if not os.path.exists(imageDir):
        os.makedirs(imageDir)
    # get the number of images for this employee
    numImages = len([f for f in os.listdir(imageDir) if f.endswith('.enc')])
    if numImages > 5:
        # we have too many images, remove the smallest face
        smallestFaceFile = None
        smallestFaceArea = 999999
        for file in os.listdir(imageDir):
            if file.endswith('.png') or file.endswith('.jpg'):
                img = cv2.imread(imageDir + file)
                area = img.shape[0] * img.shape[1]
                if area < smallestFaceArea:
                    smallestFaceArea = area
                    smallestFaceFile = file.splt('.')[0]
                    smallestFaceExt = file.split('.')[1]

        if smallestFaceFile is not None:
            # rename the face files
            os.rename(imageDir + smallestFaceFile + '.enc', imageDir + smallestFaceFile + '.encOLD')
            os.rename(imageDir + smallestFaceFile + '.' + smallestFaceExt, imageDir + smallestFaceFile 
                      + '.' + smallestFaceExt + 'OLD')
            face.save(imageDir)
    else:
        face.save(imageDir)

if __name__ == "__main__":
    logDir = 'C:\\Users\\jwatts\\pythonstuff\\project\\logs\\'

    debug = True
    target = '.\\downloadedvideos\\ACCC8EA989FF_20241101_113852.mkv'

    startTime = time.time()
    print(f'loading active employees...', end='')
    activeEmployees = loadActiveEmployees()
    endTime = time.time()
    print(f'loaded {len(activeEmployees)} active employees in {endTime - startTime} seconds')
    inactiveEmployees = loadInactiveEmployees()
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