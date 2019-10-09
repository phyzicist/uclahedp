#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr 18 13:08:55 2019

@author: peter
This file contains filtering routines
"""
from uclahedp.tests import synthdata

import matplotlib.pyplot as plt
import numpy as np



def fancyFFTFilter(f, dt, band=(None,None), axis=0, mode='pass', plots=False):
    """
    band -> (start, end)
    mode -> 
        'pass' -> Allow through only frequencies in band
        'block' -> Block filters in band
    """

    
    nf = f.shape[axis]
    fft = np.fft.fft(f, axis=axis)
    freq = np.fft.fftfreq(nf, d=dt)
    
    
    #Find endpoints of the bandpass window
    if band[0] is None or band[0] ==0 :
        a = 1
    else:
        a = np.argmin(np.abs(freq - band[0]))
           
    if band[1] is None:
        b = int(nf/2) #Set to the nyquist frequency (highest freq bin)
    else:
        b = np.argmin(np.abs(freq - band[1]))

    mask = np.zeros(fft.shape)
    
    
    #Assemble mask slice
    posslice = []
    negslice = []
    
    maskshape = []
    for i,n in enumerate(mask.shape):
        if i==axis:
            posslice.append( slice(a,b,None) )
            negslice.append( slice(-b,-a,None) )
            maskshape.append(b-a)
        else:
            posslice.append( slice(None,None,None) )
            negslice.append( slice(None,None,None) )
            maskshape.append(1)
    mask[tuple(posslice)] = np.hanning(b-a).reshape(maskshape)
    mask[tuple(negslice)] = np.hanning(b-a).reshape(maskshape)
    
    
    
    if plots:
        fig, ax = plt.subplots(figsize = [4, 4])
        if fft.ndim == 1:
            ax.plot(freq, fft/np.max(fft))
            ax.plot(freq, mask)
            ax.set_xlim(0.25*freq[a],4*freq[b])
    
    if mode == 'pass':
        fft = fft*mask
    elif mode == 'block':
        fft = fft - fft*mask
    elif mode == 'none':
        #Including this case for testing
        pass
    

        
    f = np.fft.ifft(fft, axis=axis)

    return f




def fftFilter(f, dt, band=(None,None), mode='pass', plots=False):
    """
    band -> (start, end)
    mode -> 
        'pass' -> Allow through only frequencies in band
        'block' -> Block filters in band
    
    """
    nf = f.size
    
    #Pad
    f = np.pad(f, pad_width=nf, mode='wrap')
    #Put a hamming window over the whole padded array
    f = np.hanning(3*nf)*f
    
    fft = np.fft.fft(f)
    
    freq = np.fft.fftfreq(3*nf, d=dt)
    pfreq = freq[0:int(1.5*nf)]
    
    if band[0] is None:
        a = 0
    else:
        a = np.argmin(np.abs(band[0] - pfreq))
        
    if band[1] is None:
        b = int(1.5*nf)
    else:
        b = np.argmin(np.abs(band[1] - pfreq))
        
    mask = np.zeros(3*nf) 
    mask[a:b] =  np.hanning(b-a)
    mask[3*nf-b:3*nf-a] =  np.hanning(b-a)
    
    
    if plots:
        fig, ax = plt.subplots()
        ax.plot(freq)
        ax.plot(mask)
        ax.axvline(x=a, color='green')
        ax.axvline(x=b, color='red')
        
        ax.plot(fft)
        plt.show()
        
    f = np.real(np.fft.ifft(fft*mask))
    #Divide back out the mask that was originally applied in time space
    
    f = f/np.hanning(3*nf)
    f = f[nf:2*nf] #Trim
    
    if plots:
        plt.plot(f)
        plt.show()
    
    return f
    
    
    
    
   
   
    

def lowpassFilter2D(arr, dx, dy, cutoff=10, plots=False):

    
    nx, ny = arr.shape
    fft = np.fft.fft2(arr)
    fft = np.fft.fftshift(fft)
    
    
    xfreq = np.fft.fftfreq(nx, d=dx)[0:int(nx/2.0)]
    yfreq = np.fft.fftfreq(ny, d=dy)[0:int(ny/2.0)]
    
    #Calculate the width of the hanning window that would cutoff 
    #at the cutoff frequency for this array
    dxfreq = np.mean(np.gradient(xfreq))
    a = (cutoff/dxfreq)*2
    dyfreq = np.mean(np.gradient(yfreq))
    b = (cutoff/dyfreq)*2
    

    """
    xi = np.argmin(np.abs(xfreq - cutoff))
    yi = np.argmin(np.abs(yfreq - cutoff))
    a = xfreq[0:xi].size*2
    b = yfreq[0:yi].size*2
    """

    #Deal with odd/even sizes here so padding will be integers
    if a % 2 == 1:
        a = a - 1 
    if b % 2 == 1:
        b = b - 1 
    
    mask = np.outer(np.hanning(a), np.hanning(b))
    
    #Trim or pad the mask as necessary to make it fit the data array
    if a < nx:
         xpad = int((nx - a)/ 2)
         mask = np.pad(mask, pad_width=((xpad,xpad), (0,0)), mode='constant')
    else:

         mask = mask[int(a/2 - nx/2):int(a/2 + nx/2), :]

         
    if b < ny:
         ypad = int((ny- b)/2)
         mask = np.pad(mask, pad_width=((0,0), (ypad,ypad)), mode='constant')
    else:
         mask = mask[:,int(b/2 - ny/2):int(b/2 + ny/2)]

    print(arr.shape)
    print(mask.shape)
    
    
    if plots:
        plt.pcolormesh(mask)
        plt.show()
    
    fft = np.fft.ifftshift(mask*fft)
    arr = np.fft.ifft2(fft)


    return arr


    
    

    
    
    
    
if __name__ == '__main__':
    
    
    dk, x, y, arr = synthdata.wavey2D()
    
    lowpassFilter2D(arr, dk, dk, cutoff =.2/dk, plots=True)
    
    #f = arr[:,0]
    
    #fftFilter(f, .1, plots=True, band=(1, 4))
    
    """
    dk, x, y, arr = synthdata.wavey2D()
    
    fig, ax = plt.subplots(figsize = [4, 4])
    cplot = ax.contourf(x, y, arr.T, levels=50, vmin=-1, vmax=1)
    
    
    arr = fftFilter(arr, dk, band=(15, None), mode='pass', axis=0, plots=False)
    
    fig, ax = plt.subplots(figsize = [4, 4])
    cplot = ax.contourf(x, y, arr.T, levels=50, vmin=-1, vmax=1)
    
    
    
    dt, t, arr = synthdata.twoWavePackets()
    
    f = fftFilter(arr, dt, band=(4e6, 8e6), mode='none', axis=0, plots=True)
    
    plt.plot(t*1e6, f)
    plt.xlim(0,100)
    plt.show()
    """

