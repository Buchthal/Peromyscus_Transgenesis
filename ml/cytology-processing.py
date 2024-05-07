import cv2 
import numpy as np
import os
import cv2
import matplotlib.pyplot as plt
import pandas as pd
import multiprocessing

# detect image blurriness
def is_blur(image,thres=6):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    fm = cv2.Laplacian(gray, cv2.CV_64F).var()
    return fm < thres:



# find images in the directory
path='/mnt/work3/jsb/usb/'
# recursively find all the files in the directory
files = []
for r, d, f in os.walk(path):
    for file in f:
        files.append(os.path.join(r, file))
images = [file for file in files if file.endswith('.tif')]
print(images)

mouselabeldf=pd.read_excel('jsb-mice-labels.xlsx')
#divide the images into 24 groups
images = np.array_split(images, 24)
# read the images
def is_enough_cells(image,isVisualize=False):
    cells=0
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    th, th3 = cv2.threshold(gray, 1, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
       
    cnts = cv2.findContours(th3, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE )
            
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
            
    minimum_area = 15
            #cells = 0
    for c in cnts:
        area = cv2.contourArea(c)
        x,y,w,h = cv2.boundingRect(c)
        hull=cv2.convexHull(c)
        ha=cv2.contourArea(hull)
        if ha>5:
            mask = np.zeros(image.shape[:2],np.uint8)
                
            cv2.drawContours(mask, [c], 0,255,-1)
            meanColor=cv2.mean(image,mask = mask)

            if np.std(meanColor[:3])<5:
                continue
            if isVisualize:
                
                cv2.rectangle(image,(x,y),(x+w,y+h),(36,255,12),1)
                cv2.imshow('image', image)
                cv2.imshow('th3', th3)
                cv2.imshow('mask', mask)
                cv2.waitKey(0)
            else:
                cells += 1
                if cells>30:
                    return True
    return False
def clean_data_worker(images, mouselabeldf=mouselabeldf, is_enough_cells=is_enough_cells, is_blur=is_blur):
    for i,img in enumerate(images):
        image = cv2.imread(img)
        print(i)
        if not is_blur(image) and is_enough_cells(image):
        # resize image to 244x244
            image = cv2.resize(image, (244, 244))
            mouseid=int(img.split('/')[-1].split('-')[0])
            estrusstage=mouselabeldf[mouselabeldf['Mouse ID']==mouseid]['Estrous Status on Swabbing Day'].values[0]
        
            writepath=f"{estrusstage}"
       
            # save the image as jpg
            cv2.imwrite(writepath+img.split('/')[-1].replace('.tif','.jpg'), image)


if __name__ == '__main__':
    pool=multiprocessing.Pool(24)
    pool.map(clean_data_worker, images)
    pool.close()
    pool.join()

