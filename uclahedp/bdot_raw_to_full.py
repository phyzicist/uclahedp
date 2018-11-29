#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bdot_raw_to_full.py: BDOT analysis package

Created on Wed Nov 28 13:37:21 2018

@author: peter
"""
import csvtools
import numpy as np
import os
from shutil import copyfile

def bdot_raw_to_full(rawfilename, csvdir, tdiode_hdf=None, fullfilename=None):
    
    # ******
    # Load data from the raw HDF file
    # ******
    with h5py.File(rawfilename, 'r') as f:
        data = f['data'][:]
        pos = f['pos'][:]
    
        
        run = f.attrs['run']
        probe = f.attrs['probe_name']
        
        nti = f.attrs['nti']
        npos = f.attrs['npos']
        nreps = f.attrs['nreps']
        nchan = f.attrs['nchan']
        
        daq = f.attrs['daq']
        plane = f.attrs['plane']
        drive = f.attrs['drive']
        dt = f.attrs['dt'] #dt MUST be in s for this algorithm to work...

    
    # ******
    # Load data from bdot runs csv
    # ******
    bdot_runs_csv = csvdir + "bdot_runs.csv"
    bdot_runs_csv = csvtools.opencsv(bdot_runs_csv)
    
    xatten = csvtools.findvalue(bdot_runs_csv, 'xatten', run=run, probe=probe)
    yatten = csvtools.findvalue(bdot_runs_csv, 'yatten', run=run, probe=probe)
    zatten = csvtools.findvalue(bdot_runs_csv, 'zatten', run=run, probe=probe)
    atten = np.array([xatten, yatten, zatten])
    
    xpol = csvtools.findvalue(bdot_runs_csv, 'xpol', run=run, probe=probe)
    ypol = csvtools.findvalue(bdot_runs_csv, 'ypol', run=run, probe=probe)
    zpol = csvtools.findvalue(bdot_runs_csv, 'zpol', run=run, probe=probe)
    pol = np.array([xpol, ypol, zpol])
    
    probe_origin_x = csvtools.findvalue(bdot_runs_csv, 'probe_origin_x', run=run, probe=probe)
    probe_origin_y = csvtools.findvalue(bdot_runs_csv, 'probe_origin_y', run=run, probe=probe)
    probe_origin_z = csvtools.findvalue(bdot_runs_csv, 'probe_origin_z', run=run, probe=probe)
    probe_origin = np.array([probe_origin_x, probe_origin_y, probe_origin_z])

    gain = csvtools.findvalue(bdot_runs_csv, 'gain', run=run, probe=probe)
    probe_rot = csvtools.findvalue(bdot_runs_csv, 'probe_rot', run=run, probe=probe)

    # ******
    # Load data from bdot probes csv
    #*******
    bdot_probes_csv = csvdir + "bdot_probes.csv"
    bdot_probes_csv = csvtools.opencsv(bdot_probes_csv)
    
    xarea = csvtools.findvalue(bdot_probes_csv, 'xarea',  probe=probe)
    yarea = csvtools.findvalue(bdot_probes_csv, 'yarea',  probe=probe)
    zarea = csvtools.findvalue(bdot_probes_csv, 'zarea',  probe=probe)
    area = np.array([xarea, yarea, zarea])
    nturns = csvtools.findvalue(bdot_probes_csv, 'num_turns',  probe=probe)
    
    # ******
    # Load data from main runs csv
    # ******
    main_runs_csv = csvdir + "main_runs.csv"
    main_runs_csv = csvtools.opencsv(main_runs_csv)
    
    target_xpos = csvtools.findvalue(main_runs_csv, 'target_xpos', run=run)
    target_ypos = csvtools.findvalue(main_runs_csv, 'target_ypos', run=run)
    target_zpos = csvtools.findvalue(main_runs_csv, 'target_zpos', run=run)
    target_pos = np.array([target_xpos, target_ypos, target_zpos])
    
    # TODO: add this functionality
    if tdiode_hdf is not None:
        print("Handle tdiode correction here...")
        
    # Create an array of calibration coefficents
    atten = np.power([10,10,10], atten/20.0) # Convert from decibels
    # Required input units
    # dt -> s
    # area -> mm^2
    cal = 1.0e16*dt*atten/gain/(nturns*area)
    print(cal)

    #Integrate the data
    bx = cal[0]*pol[0]*np.cumsum(data[:, :, :, 0], axis=0)
    by = cal[1]*pol[1]*np.cumsum(data[:, :, :, 1], axis=0)
    bz = cal[2]*pol[2]*np.cumsum(data[:, :, :, 2], axis=0)
    
    
    # Correct for probe rotation (generally accidental...)
    # This is rotation about the probe's main (x) axis
    if probe_rot is not 0:
        probe_rot = np.deg2rad(probe_rot)
        by = by*np.cos(probe_rot) - bz*np.sin(probe_rot)
        bz = bz*np.cos(probe_rot) + by*np.sin(probe_rot)

    #Reassemble the data array, correcting for angles due to the drive
    
    if drive in ['none', 'cartesian_xyz' ]:
        data[:, :, :, 0] = bx
        data[:, :, :, 1] = by
        data[:, :, :, 2] = bz
    elif drive in ['xy','polar_xy']:
        # Calculate the angle made by the probe shaft at each pos
        angle = np.arctan(pos[1,:]/pos[0,:])
        # The remainder of this mess creates a matrix ready for multiplication
        theta = np.outer(np.ones(nti), angle)
        theta = theta.flatten()
        theta = np.outer(theta,np.ones(nreps))
        theta = np.reshape( theta.flatten(), [nti,npos, nreps])
    
        data[:, :, :, 0] = bx*np.cos(theta) - by*np.sin(theta)
        data[:, :, :, 1] = by*np.cos(theta) + bx*np.sin(theta)
        data[:, :, :, 2] = bz
    elif drive in ['xz','polar_xz']:
        # Calculate the angle made by the probe shaft at each pos
        angle = np.arctan(pos[2, :]/pos[0, :])
        # The remainder of this mess creates a matrix ready for multiplication
        theta = np.outer(np.ones(nti), angle)
        theta = theta.flatten()
        theta = np.outer(theta,np.ones(nreps))
        theta = np.reshape( theta.flatten(), [nti,npos, nreps])
        
        data[:, :, :, 0] = bx*np.cos(theta) - bz*np.sin(theta)
        data[:, :, :, 1] = by
        data[:, :, :, 2] = bz*np.cos(theta) + bx*np.sin(theta)
    else:
        print("Invalid drive type: " + drive)
        return None


    #If necessary, come up with a new filename
    if fullfilename is None:
        rawdir = os.path.dirname(rawfilename) + '/'
        fullfilename = rawdir + 'run' + str(run) + '_' + str(probe) + '_full.h5'
        
    copyfile(rawfilename, fullfilename)
    
    #Change the relevant variables in the previous HDF file
    with h5py.File(fullfilename, 'a') as f2:
        f2['data'][...] = data # The [...] is essential for overwriting data, but I don't understand what it does...
        f2["data"].attrs['unit'] = 'G'
        f2.attrs['data_type'] = 'full'
        f2.attrs['chan_labels'] =  [s.encode('utf-8') for s in ['BX', 'BY', 'BZ']] # Note 'utf-8' syntax is a workaround for h5py issue: https://github.com/h5py/h5py/issues/289 

    return fullfilename


if __name__ == "__main__":
    csvdir = r"/Volumes/PVH_DATA/LAPD_Mar2018/METADATA/CSV/"
    rawfilename = r"/Volumes/PVH_DATA/LAPD_Mar2018/RAW/run56_LAPD1_pos_raw.h5"
    #rawfilename = r"/Volumes/PVH_DATA/LAPD_Mar2018/RAW/run102_PL11B_pos_raw.h5"
    full_file = bdot_raw_to_full(rawfilename, csvdir)
    print('Done')