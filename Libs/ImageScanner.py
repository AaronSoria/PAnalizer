import os
import sys
import datetime
from pathlib import Path

import imutils
import cv2
import numpy as np
import matplotlib.pyplot as plt
from imutils.object_detection import non_max_suppression
from imutils import paths




def BodySearch(imagen):
    bodies = []
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    # Capturo los puntos en donde posiblemente se encuentre la persona
    imagen = imutils.resize(imagen, width=min(400, imagen.shape[1]))
    rects, weights = hog.detectMultiScale(imagen,winStride=(8, 8),
                                          padding=(16, 16),scale=1.05)    
    rects = np.array([[x, y, x + w, y + h] for (x, y, w, h) in rects])
    pick = non_max_suppression(rects, probs=None, overlapThresh=0.65)    
    for (x, y, w, h) in pick:
        body = imagen[y:y+w, x:x+h]
        bodies.append(body)
    return bodies

def BinarizeImage(image):
    hsvImg = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    minValue = np.array([0,58,40])
    maxValue = np.array([35,174,255])
    binImg = cv2.inRange(hsvImg, minValue, maxValue)
    return binImg


def SkinScan(image):
    whitePixels = 0
    image = BinarizeImage(image)
    height, width = image.shape
    for x in range(height):
        for y in range(width):
            if (image[x][y]==255): whitePixels+=1
    result = whitePixels/(height * width)
    if (result>0.25):
        return True
    else:
        return False

def FaceSearchForTrainig(photo):
    gray = cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY)
    xmlSource = os.path.dirname(os.path.realpath(__file__))
    face_cascade = cv2.CascadeClassifier(str((os.path.join(xmlSource, str('haarcascade_frontalface_default.xml')))))
    faces = face_cascade.detectMultiScale(gray,scaleFactor=1.2, minNeighbors=5)
    if (len(faces) == 0):
            face_cascade = cv2.CascadeClassifier(str((os.path.join(xmlSource, str('haarcascade_frontalface_alt2.xml')))))
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
            if (len(faces) == 0):
                face_cascade = cv2.CascadeClassifier(str((os.path.join(xmlSource, str('haarcascade_frontalface_alt.xml')))))
                faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
                if (len(faces) == 0):
                    face_cascade = cv2.CascadeClassifier(str((os.path.join(xmlSource, str('haarcascade_frontalface_alt_tree.xml')))))                    
                    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
                    if (len(faces) == 0):
                        face_cascade = cv2.CascadeClassifier(str((os.path.join(xmlSource, str('haarcascade_profileface.xml')))))
                        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
                        if (len(faces) == 0):
                            return None, None
    (x, y, w, h) = faces[0]
    return gray[y:y+w, x:x+h], faces[0]



def FaceSearchForRecognize(photo):
    gray = cv2.cvtColor(photo, cv2.COLOR_BGR2GRAY)
    allFaces = []
    allGray = []
    
    xmlSource = (os.path.dirname(os.path.realpath(__file__)))
    face_cascade = cv2.CascadeClassifier(str((os.path.join(xmlSource, str('haarcascade_frontalface_default.xml')))))
    faces1 = face_cascade.detectMultiScale(gray,scaleFactor=1.2, minNeighbors=5)
    if len(faces1) != 0:
        for item in faces1:
            (x, y, w, h) = item
            allGray.append(gray[y:y+w, x:x+h])
            allFaces.append(item)
    
    face_cascade = cv2.CascadeClassifier(str((os.path.join(xmlSource, 'haarcascade_frontalface_alt2.xml'))))
    faces2 = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
    if len(faces2) != 0:
        for item in faces2:
            (x, y, w, h) = item
            allGray.append(gray[y:y+w, x:x+h])
            allFaces.append(item)
    
    face_cascade = cv2.CascadeClassifier(str((os.path.join(xmlSource, 'haarcascade_frontalface_alt.xml'))))
    faces3 = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
    if len(faces3) != 0:
        for item in faces3:
            (x, y, w, h) = item
            allGray.append(gray[y:y+w, x:x+h])
            allFaces.append(item)
    
    face_cascade = cv2.CascadeClassifier(str((os.path.join(xmlSource, 'haarcascade_frontalface_alt_tree.xml'))))
    faces4 = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
    if len(faces4) != 0:
        for item in faces4:
            (x, y, w, h) = item
            allGray.append(gray[y:y+w, x:x+h])
            allFaces.append(item)
    
    face_cascade = cv2.CascadeClassifier(str((os.path.join(xmlSource, 'haarcascade_profileface.xml'))))
    faces5 = face_cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=5)
    if len(faces5) != 0:
        for item in faces5:
            (x, y, w, h) = item
            allGray.append(gray[y:y+w, x:x+h])
            allFaces.append(item)
    
    return allGray, allFaces



def MakeTrainingDataSet(directory):
    faces=[]
    labels=[]
    for fileName in os.listdir(directory):
        fullName = str(os.path.join(directory, fileName))
        picture = cv2.imread(fullName)
        if picture is not None:            
            face, rect = FaceSearchForTrainig(picture)
            if face is not None:
                faces.append(face)
                labels.append(1)
    return faces, labels

def TrainRecognizer(directory):
    faceRecognizer = cv2.createLBPHFaceRecognizer()
    faces , labels = MakeTrainingDataSet(directory)
    faceRecognizer.train(faces,np.array(labels))
    return faceRecognizer

def Recognize(faceRecognizer,image,distance):
    persons, rects = FaceSearchForRecognize(image)
    if not persons is None or len(persons) != 0:
        for item in persons:
            label = faceRecognizer.predict(item)
            if (label[1]<distance):
                return True
            else:
                return False

