# -*- coding: utf-8 -*-
"""
Created on Sun Jun 20 00:15:52 2021

@author: Equipo
"""

from scipy.io import loadmat
import os
import cv2 as cv

def parseDataBase(pathImage,pathAnnotation):
    
    clasesImagenes = os.listdir(pathImage)
    clasesAnnotations = os.listdir(pathAnnotation)
    clasesImagenes.sort()
    clasesAnnotations.sort()
#    print(clasesImagenes)
#    print(clasesAnnotations)
    numeroImagen = 0
    numeroClase = -1
    for i,j in zip(clasesImagenes,clasesAnnotations):
#        print(i,j)
        numeroClase += 1
        imagenes = os.listdir(os.path.join(pathImage,i))
        anotaciones = os.listdir(os.path.join(pathAnnotation,j))
        imagenes.sort()
        anotaciones.sort()
        
        for z in range(len(imagenes)):
            
            if z <= int(len(imagenes)*0.7):
                
                imagen = cv.imread(os.path.join(pathImage,i,imagenes[z]))
                alto, ancho, canales = imagen.shape

                coordenadas = loadmat(os.path.join(pathAnnotation,j,anotaciones[z]))["box_coord"]
                y,h,x,w = coordenadas[0]
                
                xCenter = (((w-x)/2) + x) / ancho
                yCenter = (((h-y)/2) + y) / alto
#                xCenter = ((x+w)/2) / ancho
#                yCenter = ((y+h)/2) / alto
                width = (w-x)/ancho
                heigh = (h-y)/alto
                
                cv.imwrite(os.path.join('images','train','im'+str(numeroImagen)+'.jpg'),imagen)
                file = open(os.path.join('labels','train','im'+str(numeroImagen)+'.txt'), "w")
                file.write(str(numeroClase) + ' ' + str(xCenter) + ' ' + str(yCenter) + ' ' + str(width) + ' ' + str(heigh))
                file.close()
                numeroImagen += 1
            
            elif z<= (int(len(imagenes)*0.7) + int(len(imagenes)*0.2)):
                
                imagen = cv.imread(os.path.join(pathImage,i,imagenes[z]))
                alto, ancho, canales = imagen.shape
                
                coordenadas = loadmat(os.path.join(pathAnnotation,j,anotaciones[z]))["box_coord"]
                y,h,x,w = coordenadas[0]
                
                xCenter = (((w-x)/2) + x) / ancho
                yCenter = (((h-y)/2) + y) / alto
#                xCenter = ((x+w)/2) / ancho
#                yCenter = ((y+h)/2) / alto
                width = (w-x)/ancho
                heigh = (h-y)/alto
                
                cv.imwrite(os.path.join('images','test','im'+str(numeroImagen)+'.jpg'),imagen)
                file = open(os.path.join('labels','test','im'+str(numeroImagen)+'.txt'), "w")
                file.write(str(numeroClase) + ' ' + str(xCenter) + ' ' + str(yCenter) + ' ' + str(width) + ' ' + str(heigh))
                file.close()
                numeroImagen += 1
            
            else:
                
                imagen = cv.imread(os.path.join(pathImage,i,imagenes[z]))
#                print(os.path.join(pathImage,i,imagenes[z]))
                alto, ancho, canales = imagen.shape
                
                coordenadas = loadmat(os.path.join(pathAnnotation,j,anotaciones[z]))["box_coord"]
#                print(os.path.join(pathAnnotation,j,anotaciones[z]))
                y,h,x,w = coordenadas[0]
                xCenter = (((w-x)/2) + x) / ancho
                yCenter = (((h-y)/2) + y) / alto
#                xCenter = ((x+w)/2) / ancho
#                yCenter = ((y+h)/2) / alto
                width = (w-x)/ancho
                heigh = (h-y)/alto
#                print('x: {} y:{}, finX:{}, finY:{}, ancho:{}, alto:{}, anchoImagen:{}, altoImagen:{}'.format(x,y,w,h,w-x,h-y,ancho,alto))
                
                cv.imwrite(os.path.join('images','val','im'+str(numeroImagen)+'.jpg'),imagen)
                file = open(os.path.join('labels','val','im'+str(numeroImagen)+'.txt'), "w")
                file.write(str(numeroClase) + ' ' + str(xCenter) + ' ' + str(yCenter) + ' ' + str(width) + ' ' + str(heigh))
                file.close()
                numeroImagen += 1
            

#filepath = 'Annotations/ant/annotation_0001.mat'
#coordenadas = loadmat(filepath)["box_coord"]
#print(coordenadas)
#y,h,x,w = coordenadas[0]
#print('x: {} y:{}, finX:{}, finY:{}'.format(x,y,w,h))


pathAnnotation = 'Annotations'
pathImage = '101_ObjectCategories'
parseDataBase(pathImage, pathAnnotation)