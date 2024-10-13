# Process all files in the specified directory and save all the individual face images 
# and their encodings that can be found in each video file.  The encodings will be used 
# for facial recognition later.  The images will not be used for facial recognition, but
# are saved for debugging purposes and to allow the user to see the faces that were found.

import os
import time
import facerecogutils as fr
import sys
import datetime as dt

folder = 'C:\\Users\\jwatts\\pythonstuff\\project\\videos\\training\\'
logDir = 'C:\\Users\\jwatts\\pythonstuff\\project\\logs\\'
# keep track of the files that have been processed so this program can be stopped and restarted
processedFiles = []
processedFilesFile = folder+'processedFiles.txt'
if os.path.exists(processedFilesFile):
    with open(processedFilesFile, 'r') as f:
        for line in f:
            processedFiles.append(line.strip())
    print(f'previously processed {len(processedFiles)} files')

trainingLog = folder+'traininglog.csv'

for filename in os.listdir(folder):
    if filename.endswith('.asf'):
        if filename in processedFiles:
            print(f'skipping {filename}')
            continue
        print(f'processing {filename}')
        start = time.time()
        faces = fr.findFacesInVideo(folder+filename)
        uniqueFaces = []
        if len(faces) > 0:
            for face in faces:
                face.save(logDir)
            uniqueFaces = fr.getUniqueFaces(faces)
            print(f'    found {len(uniqueFaces)} faces')
            for uniqueFace in uniqueFaces:
                print(f'        {fr.hashFaceEncoding(uniqueFace.faceEncoding)}')
        else:
            print('    found 0 faces')
        end = time.time()
        processedFiles.append(filename)
        with open(processedFilesFile, 'a') as f:
            f.write(filename + '\n')
        print(f'    completed in {end - start} seconds')
        sys.stdout.flush()
        with open(trainingLog, 'a') as l:
            l.write(f'{dt.datetime.fromtimestamp(start).strftime("%m/%d/%Y %H:%M:%S")},{filename},{len(uniqueFaces)},{end - start}\n')

print('done')
