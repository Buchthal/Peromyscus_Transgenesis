import numpy as np
import matplotlib.pyplot as plt
import glob
import seaborn as sns
import pandas as pd
import plotly.express as px
import plotly.io as pio
import datetime
from analyze_data import fetch_data, make_figure, analyze_data
dateranges=[((24,31),(14,19),(14,30),(1,14)),
            ((24,31),(1,19),(0,0)),
            ((24,31),(1,19),(0,0)),
            ((24,31),(1,19),(0,0)),
            ((24,31),(1,19),(0,0)),
            ]
cams=['3']
metric='norm'

def remove_short_act(data,thres,intervalL=10,intervalU=100):
        idxs=[]
        
        isAct=False
        for i in range(len(data)-1):
            if data[i]>thres:
                
                isAct=True
                idxs.append(i)
            else:
                
                if isAct:
                    if len(idxs)<intervalL or len(idxs)>intervalU:
                        # data[idxs]=0
                        data[idxs]=np.mean(data[[idxs[0]-1,idxs[-1]+1]])
                
                isAct=False
                idxs=[]
        return data



def get_diff_from_norm(normArr, diffdata):
    
    for i in range(len(normArr)-1):
        if normArr[i]<-1 :
            normArr[i]=0
        else:
            normArr[i]=np.abs((diffdata[i]-diffdata[i+1])/(diffdata[i]+1))
    return normArr
#calculate moving average over every 10 frames
def get_moving_avg(diff):
    moving_avg=[]
    for i in range(len(diff)-10):
        moving_avg.append(np.mean(diff[i:i+10]))
    return np.array(moving_avg)

cropstr='qtr'
for i,cam in enumerate(cams):
    files=glob.glob(f'{cam}_TwoPoints_{cropstr}_{metric}_*.npy')
    filesac=[]
    filesdiff=[]
    for j in range(4):
        if j==0:
            continue
            filesac.extend( [f'{cam}_TwoPoints_{cropstr}_{metric}_07{"%02d"%k}.npy' for k in range(dateranges[i][j][0],dateranges[i][j][1]+1)])
        elif j==1:
            continue
            filesac.extend( [f'{cam}_TwoPoints_{cropstr}_{metric}_08{"%02d"%k}.npy' for k in range(dateranges[i][j][0],dateranges[i][j][1]+1)])
        elif j==2:
            filesac.extend([ f'{cam}_TwoPoints_{cropstr}_{metric}_09{"%02d"%k}.npy' for k in range(dateranges[i][j][0],dateranges[i][j][1]+1)])
            filesdiff.extend([ f'{cam}_TwoPoints_{cropstr}_diff_09{"%02d"%k}.npy' for k in range(dateranges[i][j][0],dateranges[i][j][1]+1)]) 
        elif j==3:
            filesac.extend([ f'{cam}_TwoPoints_{cropstr}_{metric}_10{"%02d"%k}.npy' for k in range(dateranges[i][j][0],dateranges[i][j][1]+1)])
            filesdiff.extend([ f'{cam}_TwoPoints_{cropstr}_diff_10{"%02d"%k}.npy' for k in range(dateranges[i][j][0],dateranges[i][j][1]+1)])
    files=filesac
    files.sort()
    print(files)
    from skimage.measure import block_reduce
    datas=[]
    windows=[datetime.time(i,j,k) for i in range(24) for j in range(60) for k in range(0,60,4)]
    dates=[]
    cyclingFlags=[]
    datetimeidxs=[]
    diffdatas=[]
    for i,file in enumerate(files):
        datas.append(np.load(file)[:21600])
        diffdatas.append(np.load(file.replace('norm','norm'))[:21600])
        # convert date string to datetime object
        datestr=file.split('.')[-2].split('_')[-1]
        date=datetime.date.fromisoformat(f'2023-{datestr[:2]}-{datestr[2:]}')
        dates.extend([date]*len(windows))
        datetimeidxs.extend([datetime.datetime.combine(date,window) for window in windows])
        cyclingFlags.extend([i%4]*len(windows))
    # repeat windows for each date
    windows=np.array(windows*len(files))
    dates=np.array(dates)


    # Pad each array to the maximum size
    padded_datas = []
    datasums=[]
    datasumsac=[]
    newdatas=[]
    


    for file,data,diffdata in zip(files,datas,diffdatas):
        data=get_diff_from_norm(data,diffdata)
        data=np.where(data>300,1,0)
        newdatas.append(data)
        
        datasums.append(sum(data[:3200]))
        if file in filesac:
            datasumsac.append(sum(data))
    datasums=np.array(datasums)
    datasumsac=np.array(datasumsac)
    # Convert list of padded arrays to matrix
    matrix = np.vstack(newdatas)
    # covert matrix to 2D array
    # flatten matrix
    matrix_flat = matrix.flatten()
    datadf=pd.DataFrame({'diff':matrix_flat,'datetime':datetimeidxs,'cycling':cyclingFlags})
    datadf=datadf.resample('5min',on='datetime').mean()
    datadf['date']=datadf.index.date
    datadf['window']=datadf.index.time
    # cacluate moving average of datadf by window
    
    make_figure(datadf,cam,f'{cam}_heatmap.html')

    make_figure(datadf,cam,f'{cam}_heatmap_facet.html',isFacet=True)

    xnames=[file.split('.')[-2].split('_')[-1] for file in files]

    # Define a list of custom high contrast colors
    colors=['#000000', '#FF0000', '#00F400', '#0000FF']
    # reverse list
    colors = colors[::-1]



    plt.figure()
    sns.barplot(x=xnames, y=datasums, palette=colors)
    plt.title(f'rpi-zero2-lir-{cam} 0030-0100 UTC')
    # make xticks labels vertical
    plt.xticks(rotation=90)
    plt.savefig(f'plotham/{cam}_bar.pdf')
plt.show()
