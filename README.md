# stinger

Stinger is a software agent that detects piggybacking and tailgating to prevent unauthorized entry into a facility. The agent will interface with a facility’s existing video camera system and door badge/fob system without requiring specialized detection hardware.  The agent will run on a commodity Windows-based desktop.

This is currently a work in progress.

facerecogutils.py contains the classes and helper functions used in the system.  Uses face_recognition and numpy for face detection and face recognition.

gettrainingimages.py is used to process all video files in the specified directory and save all the individual face images and their encodings that can be found in each video file.

testrecognition.py is used to to process all video files in the specified directory and peform facial recognition on any faces found.

getmetrics.py processes a spreadsheet containing results of a run of testrecognition.  It produces a CSV file of metrics to be imported into a spreadsheet.  Uses pandas to read and excel file.
