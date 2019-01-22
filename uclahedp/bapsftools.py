#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This program opens an LAPD HDF file (as well as metadata csvs)
and creates an ndfFile object containing the data. 

@author: peter
"""

#TODO currently 'NI_XZ' isn't valid drive

import numpy as np
from astropy import units as u

import os

import hedpConstants as c
import csvtools as csvtools
#bapsflib is available from pip. Run command 'pip papsflib' from terminal to install it
from bapsflib import lapd
from bapsflib._hdf import HDFMap



# channel_arr = array of tuples of form: (digitizer, adc, board#, channel#)
# eg. channel_arr = ('SIS crate', 'SIS 3305', 2, 1)
#
# control = array of tuples of form (motion control, receptacle)
# eg. controls = [('6K Compumotor', receptacle)]
# note that 'receptacle' here is the receptacle NUMBER, 1 - indexed!)
# if no control is specified, the measurement is assumed to be stationary
def bapsfReadHDF(src=None, dest=None, channel_arr = None, controls = None ):
    
    motion = not controls == None
    nchan = len(channel_arr)
    print('motion = ' + str(motion))

    f = lapd.File(src, silent=True)
    
    arr = [] # Array for temporarily storing the read data
    for i in range(nchan):
        channel = channel_arr[i]
        data = f.read_data(channel[2], channel[3],
                           digitizer =channel[0], adc = channel[1],
                           add_controls=controls, 
                           silent=True, )
        
        
        signal = data['signal'].T
        
        # Only need to do this for one channel, since we assume
        # that all channels coorespond to a single physical probe
        if i == 0:
            shotnum = data['shotnum']
            nshots = len(shotnum)
            nti = signal.shape[0]
            clock_rate = data.info['clock rate'].to(u.Hz)
            dt =  (  1.0 / clock_rate  ).to(u.s)
            t = np.arange(nti)*dt
            chan_axis = np.arange(nchan)*u.Unit('')
            shots_axis = np.arange(nshots)*u.Unit('')
            

         # Reshape the array according to the axes read in
        if motion and gridded:
            signal = np.reshape(signal, (nti, nx, ny, nz, nreps))
        else:
            signal = np.reshape(signal, (nti, nshots))
                
       
        # Temporarily store the array
        arr.append(signal)
        
    
    axes = []
    
    # Always include a time axis in the beginning
    if nti > 1:
        axes.append( {'label':'t', 'axis':t} )
    
    
    #Deal with motional gridded datasets
    if motion and gridded:
        output = np.zeros([nti, nx, ny, nz, nreps, nchan])

        if nx > 1:
            axes.append( {'label':'x', 'axis':xaxis} )
        if ny > 1:
            axes.append( {'label':'y', 'axis':yaxis} )
        if nz > 1:
            axes.append( {'label':'z', 'axis':zaxis} )
        if nreps > 1:
            axes.append( {'label':'reps', 'axis':rep_axis} )

    #Deal with motional non-gridded datasets
    #Deal with non-motional datasets (those with no motion device set  
    #(here both of these options have the same axes and shape requirements)
    else: 
        output = np.zeros([nti, nshots, nchan])
        if nshots > 1:
            axes.append( {'label':'shots', 'axis':shots_axis} )
      
        
        
        
    #Always include a channel axis at the end if there is more than one   
    if nchan > 1:
            axes.append( {'label':'channels', 'axis':chan_axis} )
            
            
    # Create an output data array with the proper form
    
    for i in range(nchan):
        output[..., i] = arr[i]
        
    # Eliminate trivial dimensions 
    output = np.squeeze(output)
    # Set units of data to volts
    output = output*u.V
    # Set datalabel
    data_label = 'Raw LAPD data'
    
   
    
    #TODO add the pos array to the ndf object as an option and save as that type here
    obj = sdfarr(data=output, axes=axes, data_label = data_label)
    obj.appendLog('Created by bapsftools.bapsfReadHDF from HDF file: ' + filepath)
    
    return obj
  
    


def readRunProbe( run, probe, exp_dir):

    csv_dir = os.path.join(exp_dir, c.metadata_dir)

    
    probe_conts_csvs = csvtools.findCSV(csv_dir, run=None, probe=probe)
    probe_runs_csvs = csvtools.findCSV(csv_dir, run=run, probe=probe)
    
    run_level_csvs = exp_runs_csvs + exp_consts_csvs
    probe_level_csvs = probe_conts_csvs + probe_runs_csvs
    
    
    
    run_level_attrs = {}
    probe_level_attrs ={}
    
    attrs = csvtools.getAttrs(csvdict, run=)
    
    
    # Get the information we need from the csv file
    runs_csv = csvtools.opencsv(runs_csv_file)
    
    
    datafile = csvtools.findValue(runs_csv, 'datafile', run=run, probe=probe)
    
    datafile = exp_dir + c.hdf_dir + datafile + '.hdf5'
    print(datafile)

    #Check to make sure this probe exists in the file specified
    if (datafile is None):
        print("No probe found matching: " + probe + ", run " + str(run) + " in " + runs_csv_file)
        return None
    
    
    digitizer = csvtools.findValue(runs_csv, 'digitizer', run=run, probe=probe)
    adc = csvtools.findValue(runs_csv, 'adc', run=run, probe=probe)
    nchan = csvtools.findValue(runs_csv, 'nchan', run=run, probe=probe)
    
    if (digitizer is None) or (adc is None):
        print("Digitizer or ADC field(s) are missing: " + probe + ", run " + str(run) + " in " + runs_csv_file)
        return None
    
    if (nchan is None):
        print("nchan not found in csv file: assuming nchan = 1")
        nchan = 1
        

    motion_controller = csvtools.findValue(runs_csv, 'motion_controller', run=run, probe=probe)
    motion_receptacle = csvtools.findValue(runs_csv, 'motion_receptacle', run=run, probe=probe)
    gridded = csvtools.findValue(runs_csv, 'gridded', run=run, probe=probe)
   
    gridded = bool(gridded)
        
    
        
    if motion_controller is not None:
        motion = True
        
        if motion_receptacle is None:
            print("motion_receptacle not found in csv file: assuming motion_receptacle = 1")
            motion_receptacle = 1
            
        controls = [(motion_controller, motion_receptacle)]
        
   
    
    else:
        motion = False
        controls = None

    

    channel_arr = []
    for i in range(nchan):
        brd = csvtools.findValue(runs_csv, "brd" + str(i+1), run=run, probe=probe)
        chan = csvtools.findValue(runs_csv, "chan" + str(i+1), run=run, probe=probe)
        tp = (digitizer, adc, brd, chan)
        channel_arr.append(tp)
    

    #TODO add the other fields here...

    obj = bapsfReadHDF(filepath=datafile, channel_arr = channel_arr, controls = controls, gridded = gridded )

    return obj

    
    
    
if __name__ == "__main__":
    
    exp_dir = os.path.join("F:", "/LAPD_Mar2018/")


    src  = r"/F:/LAPD_Mar2018/HDF/peening074_apr09.hdf5" #Small file
    #sfile = r"/F:/LAPD_Mar2018/HDF/peening065_apr06.hdf5" #big file
    
    dest = r"/F:/LAPD_Mar2018/RAW/test_save.hdf5"

    print('reading')
    x =  readRunProbe(102, 'PL11B', exp_dir)

    print('done')
