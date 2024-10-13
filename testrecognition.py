# Process all files in the specified directory and run facial recognition on any faces found.

import os
import time
import facerecogutils as fr
import sys
import datetime as dt

folder = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\testing\\'
logDir = 'C:\\Users\\jwatts\\pythonstuff\\project\\logs\\'

testStart = time.time()
print(f'test started at {dt.datetime.fromtimestamp(testStart).strftime("%m/%d/%Y %H:%M:%S")}')

startTime = time.time()
print(f'loading active employees...', end='')
activeEmployees = fr.loadActiveEmployees()
endTime = time.time()
print(f'loaded {len(activeEmployees)} faces in {endTime - startTime} seconds')
inactiveEmployees = fr.loadInactiveEmployees()
facesToIgnore = fr.loadFacesToIgnore()

# keep track of the files that have been processed so this program can be stopped and restarted
processedFiles = []
processedFilesFile = folder+'processedFilesFR.txt'
if os.path.exists(processedFilesFile):
    with open(processedFilesFile, 'r') as f:
        for line in f:
            processedFiles.append(line.strip())
    print(f'previously processed {len(processedFiles)} files')

trainingLog = folder+'testinglogFR.csv'


for filename in os.listdir(folder):
    if filename.endswith('.asf'):
        if filename in processedFiles:
            print(f'skipping {filename}')
            continue
        print(f'processing {filename}')
        start = time.time()
        faces = fr.findFacesInVideo(folder+filename, facesToIgnore)
        uniqueFaces = []
        names = ''
        if len(faces) > 0:
            uniqueFaces = fr.getUniqueFaces(faces)
            print(f'    found {len(uniqueFaces)} faces')
            for uniqueFace in uniqueFaces:
                uniqueFace.save(logDir)
                print(f'        {fr.hashFaceEncoding(uniqueFace.encoding)}')
            fr.identifyFaces(activeEmployees, inactiveEmployees, uniqueFaces)
            print(f'    faces: ')
            for face in uniqueFaces:
                print(f'        {face.name} at {face.timestamp} seconds')
                names += face.name + ' '
        else:
            print('    found 0 faces')
        end = time.time()
        processedFiles.append(filename)
        with open(processedFilesFile, 'a') as f:
            f.write(filename + '\n')
        print(f'    completed in {end - start} seconds')
        sys.stdout.flush()
        with open(trainingLog, 'a') as l:
            l.write(f'{dt.datetime.fromtimestamp(start).strftime("%m/%d/%Y %H:%M:%S")},{filename},{len(uniqueFaces)},{names},{end - start}\n')
testEnd = time.time()
print(f'test ended at {dt.datetime.fromtimestamp(testEnd).strftime("%m/%d/%Y %H:%M:%S")}')
print(f'test completed in {(testEnd - testStart)/60} minutes')
