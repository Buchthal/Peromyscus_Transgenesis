import cv2
import numpy as np
from time import sleep
import pybgs as bgs
import sys
import glob
import multiprocessing
from PIL import Image
from math import floor
print("OpenCV Version: {}".format(cv2.__version__))

def is_cv2():
  return check_opencv_version("2.")

def is_cv3():
  return check_opencv_version("3.")

def is_lower_or_equals_cv347():
  [major, minor, revision] = str(cv2.__version__).split('.')
  return int(major) == 3 and int(minor) <= 4 and int(revision) <= 7

def is_cv4():
  return check_opencv_version("4.")

def check_opencv_version(major):
  return cv2.__version__.startswith(major)

algorithms=[]
algorithms.append(bgs.TwoPoints)

count=0
algorithm = algorithms[0]

    
def get_fg_masks(algorithm,imagepath):
    masks=[]
    files=sorted(glob.glob(imagepath+'/*.jpg'))
    frames=[]
    for file in files:
       try:
        frame=Image.open(file)
        frame=np.asarray(frame)
        frames.append(frame)
        print(f'read {file}')
       except:
        print(f'error in {file}')
    print(algorithm.__class__.__name__)
    for i,frame in enumerate(frames):
        try:
          
          # crop the image to remove top half using opencv
          




          if frame is None:
              break

          normalized=cv2.normalize(frame, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)
          
          
          

          fgMask = algorithm.apply(normalized)
          

          
          del(normalized)
          del(frame)
          
          if cv2.waitKey(30) == ord('q'):
                      break
          masks.append(fgMask)
        except:
          print(f'error in frame {i} ')
    return masks

def get_fg_masks_norm(algorithm,frames,isVis=False):
    normArr=np.zeros(10000)
    diffArr=np.zeros(10000)
    
    print(algorithm.__class__.__name__)
    for idx in range(len(frames)):
        try:
          
          frame=frames[idx][200:,320:,:]
          
          




          if frame is None:
              normArr[idx]=0

          normalized=cv2.normalize(frame, None, alpha=0, beta=255, norm_type=cv2.NORM_MINMAX)

          
          
          
        

          fgMask = algorithm.apply(normalized)
          if idx>0:
            diffArr[idx-1]=np.sum(np.abs(cv2.subtract(frames[idx],frames[idx-1])))
          if isVis:
            cv2.imshow('Frame3', frame)
            ret,thres=cv2.threshold(frame, 127, 255, cv2.THRESH_BINARY) 
            cv2.imshow('thres', thres)
            fgMask1=cv2.normalize(fgMask, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            normArr[idx]=np.linalg.norm(fgMask1)
          else:  
            fgMask=cv2.normalize(fgMask, None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            normArr[idx]=np.linalg.norm(fgMask)
          
          if isVis:
            #display the text of norm on image
            cv2.putText(fgMask, str(normArr[idx]), (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (148, 61, 70) , 2)
            cv2.imshow('FG Mask', fgMask)
            if normArr[idx]>50:
              print('present')
          
            if cv2.waitKey(30) == ord('q'):
                        break
          
          print(f'processed frame {idx}')
        except:
          normArr[idx]=0
          print(f'error in frame {idx}')
    return normArr,diffArr

def read_imgs(files,framesOut):
    frames=np.zeros(10000,dtype=object)
    for file in files:
       filename=file.split('/')[-1].split('.')[0]
       filenamesplit=filename.split('-')
       idx=int(floor((int(filenamesplit[0])*3600+int(filenamesplit[1])*60+int(filenamesplit[2]))/4))
       try:
        if int(filenamesplit[0])>11:
          break
        frame=Image.open(file)
        frame=np.asarray(frame)
        frames[idx]=frame

        print(f'read {file}')
       except:
        print(f'error in {file}')
    
    framesOut[0]=frames
      


        
#calculate the difference between the norms of two neighboring frames
def get_diff(mymasks):
   

    diff=[]
    for i in range(len(mymasks)-1):
        #normlize the mask
        mymasks[i]=cv2.normalize(mymasks[i], None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        diff.append(np.linalg.norm(mymasks[i]-mymasks[i+1]))
    return diff

def get_norm_diff(mymasks):
   

    diff=[]
    for i in range(len(mymasks)-1):
        #normlize the mask
        mymasks[i]=cv2.normalize(mymasks[i], None, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
        diff.append(np.linalg.norm(mymasks[i])-np.linalg.norm(mymasks[i+1]))
    return diff

def get_diff_from_norm(normArr):
    
    for i in range(len(normArr)-1):
       normArr[i]=np.abs(normArr[i]-normArr[i+1])
    return normArr
#calculate moving average over every 10 frames
def get_moving_avg(diff):
    moving_avg=[]
    for i in range(len(diff)-10):
        moving_avg.append(np.mean(diff[i:i+10]))
    return moving_avg

   
def run(algorithm,  cam, frames,timepoint,isVis=False):
    sub=algorithm()
    algorithmName=algorithm.__name__
    try:
      norm,diff=get_fg_masks_norm(sub,frames,isVis=isVis)
      if not isVis:
        np.save('mus/'+cam+'_'+algorithmName+'_'+'qtr_norm_'+timepoint+'.npy',norm)
        np.save('mus/'+cam+'_'+'simpleDiff'+'_'+timepoint+'.npy',diff)
    except:
      print(f'error in {cam} {timepoint}')
    print('done'+timepoint)
    frames=None

if __name__ == '__main__':

  timepoints=[] 
  for i in range(21,32):
    timepoints.append('07%02d'%i)
  for i in range(1,32):
    timepoints.append('08%02d'%i)
  for i in range(1,10):
    timepoints.append('09%02d'%i)
  cams=[]   
  cams=['254']
  isVis=False
  timepointsblks=[]
  # make blocks of 4 timepoints
  blkcount=0
  timepointblk=[]
  for timepoint in timepoints:
    if blkcount<4:
        timepointblk.append(timepoint)
        blkcount+=1
    else:
        timepointsblks.append(timepointblk)
        timepointblk=[]
        blkcount=1
        timepointblk.append(timepoint)  


  with multiprocessing.Manager() as manager:
    framesCollection1=manager.list()
    framesCollection2=manager.list()
    framesCollection1.append(None)
    framesCollection2.append(None)
    for cam in cams:
        prefetchers=[]
        toggle=True
        for i,timepoint in enumerate(timepoints):
          for algorithm in algorithms:
          #spawn a new worker for each timepoint

            if i==0:
                files=sorted(glob.glob(f'/mnt/nfs/stills/rpi-zero2-{cam}/2023/{timepoint[:2]}/{timepoint[2:]}/*.jpg'))
                read_imgs(files,framesCollection1)
                if i+1<len(timepoints):
                    files=sorted(glob.glob(f'/mnt/nfs/stills/rpi-zero2-{cam}/2023/{timepoints[i+1][:2]}/{timepoints[i+1][2:]}/*.jpg'))
                    prefetcher=multiprocessing.Process(target=read_imgs, args=(files,framesCollection2))
                    prefetcher.start()
                    prefetchers.append(prefetcher)
                run(algorithm, cam,framesCollection1[0] ,timepoint,isVis)
                toggle=not toggle
            else:
                for prefetcher in prefetchers:
                  prefetcher.join()
                if i+1<len(timepoints):
                    files=sorted(glob.glob(f'/mnt/nfs/stills/rpi-zero2-{cam}/2023/{timepoints[i+1][:2]}/{timepoints[i+1][2:]}/*.jpg'))
                    if toggle:
                      prefetcher=multiprocessing.Process(target=read_imgs, args=(files,framesCollection2))
                    else:
                      prefetcher=multiprocessing.Process(target=read_imgs, args=(files,framesCollection1))
                    prefetcher.start()
                    prefetchers.append(prefetcher)
                if toggle:
                  run(algorithm, cam,framesCollection1[0] ,timepoint,isVis)
                else:
                  run(algorithm, cam,framesCollection2[0] ,timepoint,isVis)
                toggle=not toggle
                
            
          print('done'+algorithm.__name__+cam)
  cv2.destroyAllWindows()
