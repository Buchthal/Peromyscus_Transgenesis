import numpy as np
import matplotlib.pyplot as plt
import glob
import seaborn as sns
dateranges=[((24,31),(1,19),(0,0)),
            ((24,31),(1,19),(0,0)),
            ((24,31),(1,19),(0,0)),
            ((24,31),(1,19),(0,0)),
            ((24,31),(1,19),(0,0)),
            ]
cams=['232','233','256','260','261']
for i,cam in enumerate(cams):
    files=glob.glob(f'{cam}_TwoPoints_qtr_norm_*.npy')
    filesac=[]
    for j in range(3):
        if j==0:
            filesac.extend( [f'{cam}_TwoPoints_qtr_norm_07{"%02d"%k}.npy' for k in range(dateranges[i][j][0],dateranges[i][j][1]+1)])
        elif j==1:
            filesac.extend( [f'{cam}_TwoPoints_qtr_norm_08{"%02d"%k}.npy' for k in range(dateranges[i][j][0],dateranges[i][j][1]+1)])
        elif j==2:
            filesac.extend([ f'{cam}_TwoPoints_qtr_norm_09{"%02d"%k}.npy' for k in range(dateranges[i][j][0],dateranges[i][j][1]+1)])
    
    files.sort()
    from skimage.measure import block_reduce
    datas=[]

    for file in files:
        datas.append(np.load(file))
    #covert datas to numpy ndarray with all floats
    max_rows = max(data.shape[0] for data in datas)


    # Pad each array to the maximum size
    padded_datas = []
    datasums=[]
    datasumsac=[]
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

    def get_diff_from_norm(normArr):
        
        for i in range(len(normArr)-1):
           normArr[i]=np.abs(normArr[i]-normArr[i+1])
        return normArr
    #calculate moving average over every 10 frames
    def get_moving_avg(diff):
        moving_avg=[]
        for i in range(len(diff)-10):
            moving_avg.append(np.mean(diff[i:i+10]))
        return np.array(moving_avg)


    for file,data in zip(files,datas):
        data=data[:7500]
        data=remove_short_act(data,15,3,100)
        data=get_diff_from_norm(data)
        data=np.convolve(data,np.ones(100),mode='same')
        data = block_reduce(data, (100,), np.max)
        
        padded_data = np.pad(data, (0, max_rows - data.shape[0]), 'constant',constant_values=(0,0))
        
        datasums.append(sum(data))
        if file in filesac:
            datasumsac.append(sum(data))
        padded_datas.append(padded_data)
    datasums=np.array(datasums)
    datasumsac=np.array(datasumsac)
    # Convert list of padded arrays to matrix
    matrix = np.vstack(padded_datas)
    # covert matrix to 2D array
    # flatten matrix
    matrix_flat = matrix.flatten()
    


    xnames=[file.split('.')[-2].split('_')[-1] for file in files]

    # Define a list of custom high contrast colors
    colors=['#000000', '#FF0000', '#00F400', '#0000FF']
    # reverse list
    colors = colors[::-1]



    plt.figure()
    sns.barplot(x=xnames, y=datasums, palette=colors)
    plt.title(f'{cam} 0000-0820 UTC')
    # make xticks labels vertical
    plt.xticks(rotation=90)
    plt.savefig(f'plotham/{cam}_bar.pdf')
    # plot autocorrelation of datasums
    from statsmodels.tsa.stattools import acf
    autocorr=acf(datasumsac)
    #peform Durbin–Watson test
    from statsmodels.stats.stattools import durbin_watson
    dw=durbin_watson(autocorr)
    from statsmodels.stats.diagnostic import acorr_ljungbox

    lb=acorr_ljungbox(datasumsac, lags=5)
    print(lb)

    from statsmodels.graphics.tsaplots import plot_acf
    plot_acf(datasumsac)
    daterangestr=''
    for j in range(3):
        datestart=dateranges[i][j][0]
        dateend=dateranges[i][j][1]
        if datestart!=0:
            daterangestr=daterangestr+' '+f'{7+j:02d}{datestart:02d}-{7+j:02d}{dateend:02d}'
    plt.title(f'{cam} 0000-0820 UTC; Date range: {daterangestr}')
    plt.text(0.5,0.5,str(lb))
    
    plt.savefig(f'plotham/{cam}_auto.pdf')
    
    print(dw)
plt.show()
