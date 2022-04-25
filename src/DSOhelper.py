import numpy as np
from matplotlib import pyplot as plt
from matplotlib.offsetbox import AnchoredText

"""
helper functions for reading, parsing and plotting oscilloscope data
written by yeo zhen yuan
"""

def addsubfiglabels(axx,skip=0,loc='upper left'):
    """ add subfigure labels, starting from 'a' """
    try:
        len(axx)
    except TypeError:
        return
    ascii_letters = 'abcdefghijklmnopqrstuvwxyz'*(len(axx.ravel())//26+1)
    for letter,ax in zip(ascii_letters[skip:],axx.ravel()):
        at = AnchoredText(letter,frameon=True, loc=loc)#prop=dict(size=15)
        at.patch.set_boxstyle("round,pad=0.,rounding_size=0.2")
        ax.add_artist(at)
def get_oscilloscope_data(file,headers=True,raw=False):
    """
    returns oscilloscope data as a numpy array, along with headers (default)
    set headers=False for reading data only.
    """
    data = ""
    with open(file,"r") as f:#f"{datafolder}{file}"
        data = f.readlines()
    if not headers: # returns just the data portion
        return data[25:]
    
    numCH = len(data[1].split(","))//2
    scopeHeaders=dict([(i+1,dict()) for i in range(numCH)]) # indexed from 1
    for h in data[:24]:
        h = h.split(",")
        if h[0]=="Format":
            continue
        for ch in range(1,numCH+1):
            try:
                scopeHeaders[ch][h[0]] = float(h[int((ch-1)*2+1)])
            except ValueError:
                scopeHeaders[ch][h[0]] = h[int((ch-1)*2+1)]
    if raw:
        return data[25:],scopeHeaders
    parsed_data = dict([(ch,[]) for ch in range(1,numCH+1)])
    for dd in data[25:]:
        dd = dd.split(",")
        for CH in range(1,numCH+1):
            parsed_data[CH].append(int(dd[ int((CH-1)*2) ]))
    parsed_data = dict([(ch,np.array(parsed_data[ch])) for ch in range(1,numCH+1)])
    return parsed_data,scopeHeaders
def getvoltage(oscilloscope_data,header):
    vdiv= header["Vertical Scale"]
    dv  = vdiv/25
    return oscilloscope_data*dv
def plot_scope_data(title,dataseq,headers,CH=1,ylim=False,save=""): 
    plt.title(title)
    samplingperiod = headers[CH]["Sampling Period"]
    plt.plot(np.arange(len(dataseq[CH]))*samplingperiod,getvoltage(dataseq[CH],headers[CH]))
    plt.axhline(headers[CH]["Trigger Level"],c="r",ls="--",label=f"trigger = {headers[CH]['Trigger Level']}V")
    plt.ylabel("Voltage (V)")
    if ylim:
        vpos = headers[CH]["Vertical Position"]
        vdiv = headers[CH]["Vertical Scale"]
        plt.ylim(-4*vdiv-vpos,4*vdiv-vpos)
    plt.xlabel("Time (s)")
    plt.legend()
    plt.show() if len(save)==0 else plt.savefig(save)
            
def subplot_scope_data(dataseq,headers,ax,CH=1,label="",alpha=0.3,xscale=1):
    samplingperiod = headers[CH]["Sampling Period"]
    ax.plot(np.arange(len(dataseq[CH]))*samplingperiod*xscale,getvoltage(dataseq[CH],headers[CH]),label=label,alpha=alpha)
    