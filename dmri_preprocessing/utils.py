#!/bin/env python
# Purpose: Gather all utility functions

from bids.layout import BIDSLayout
import numpy as np
import os

def get_bids_layout(bids_dir, subject_id, session_id):
    """
    Use pybids to extract information about dataset that is being processed
    """
    layout = BIDSLayout(bids_dir,validate=False)

    participant_data = {}
    participant_data['subject'] = subject_id
    participant_data['session'] = session_id
    participant_data['dwi'] = layout.get(subject=subject_id, session=session_id, return_type='file', suffix='dwi', extensions=['.nii.gz','.nii'])
    participant_data['fmap'] = layout.get(subject=subject_id, session=session_id, return_type='file', suffix='epi', extensions=['.nii.gz','.nii'])
    participant_data['sbref'] = layout.get(subject=subject_id, session=session_id, return_type='file', suffix='sbref', extensions=['.nii.gz','.nii'])

    return layout, participant_data

def edit_phase_encoding_dir_metadata(metadata):
    # In the metadata we have encoding directions as i,j and k. FSL TOPUP needs x,y or z.
    metadata['PhaseEncodingDirection'] = metadata['PhaseEncodingDirection'].replace('i','x')
    metadata['PhaseEncodingDirection'] = metadata['PhaseEncodingDirection'].replace('j','y')
    metadata['PhaseEncodingDirection'] = metadata['PhaseEncodingDirection'].replace('k','z')
    return metadata

def get_overview_of_data(subject_data, layout, b0_threshold):
    """
    Gather data from dwi and fmaps into a dictionary
    """
    data = {}

    data['dwi'] = []
    data['fmap'] = []
    data['sbref'] = []

    # dwi data
    data_types = ['dwi','fmap','sbref']
    for data_type in data_types:
        for filename in subject_data[data_type]:
            # get metadata
            metadata = layout.get_metadata(filename)
            # In the metadata we have encoding directions as i,j and k. FSL TOPUP needs x,y or z.
            metadata = edit_phase_encoding_dir_metadata(metadata)
            if data_type == 'dwi':
                # extract bvals and b0 indeces
                with open(filename.replace('nii.gz','bval')) as f_bval:
                    bval = np.array(f_bval.readline().split(" "),dtype=int)
                    b0_idx = np.where(bval<b0_threshold)
                    bhigh_idx = np.where(bval>b0_threshold)
                
                data[data_type].append(
                    {
                        'filename': filename,
                        'metadata': metadata,
                        'bval': bval,
                        'b0_idx':b0_idx[0],
                        'bhigh_idx': bhigh_idx[0]
                    }
                )
            else:
                include = False
                try:
                    if any(['dwi' in test for test in metadata['IntendedFor']]):
                        include = True
                except:
                    if os.path.exists(filename.replace("_sbref.nii.gz","_dwi.nii.gz")):
                        include = True
                if include is True:
                    data[data_type].append(
                        {
                            'filename': filename,
                            'metadata': metadata
                        }
                    )
    return data

def check_opposite_directions(encoding_directions):
    """
    Check if we have an opposite direction in the list
    """
    for dir in encoding_directions:
        if dir + "-" in encoding_directions:
            return True
    
    return False

def check_if_dataset_compatible_with_topup(data_overview):
    """
    Check if dataset inputs are compatible with topup, i.e.,
    do we have datasets in both input directions.

    Input
    =====
    data_overivew:
        dict containing data information.
    
    Output
    ======
    topup_options:
        options for running topup.
    phase_encoding_directions:
        the phase encoding directions for the different data types: dwi,
        fmap and sbref.
    """
    # For topup we need blip-up blip-down fieldmaps,
    # or one fieldmap, and one b0 inside dwi sequence
    topup_options = {}
    # options
    topup_options['do_topup'] = True

    phase_encoding_directions = {}
    for data_type in data_overview:
        # Check if data is not dwi, fmap or sbref:
        if data_type not in ['fmap','dwi','sbref']:
            continue
        phase_encoding_directions[data_type] = []
        for dataset in data_overview[data_type]:
            # Check if we have one or more b0s, if dwi
            if data_type == 'dwi' and len(dataset['b0_idx']) == 0:
                continue
            
            phase_encoding_directions[data_type].append(dataset['metadata']['PhaseEncodingDirection'])

    # Check encoding directions for all data
    dwi_fmap_encoding_directions = []
    for data_type in phase_encoding_directions:
        if(check_opposite_directions(phase_encoding_directions[data_type])):
            topup_options["only_"+data_type] = True
        else:
            topup_options["only_"+data_type] = False

        if data_type == 'dwi' or data_type == 'fmap':
            dwi_fmap_encoding_directions.extend(phase_encoding_directions[data_type])

    if(check_opposite_directions(dwi_fmap_encoding_directions)):
        topup_options['dwi_fmap_combined'] = True
    else:
        topup_options['dwi_fmap_combined'] = False
        topup_options['do_topup'] = False
    
    return(topup_options, phase_encoding_directions)

def merge_bval_bvecs(in_files,output_file_base):
    """
    Merges bvals and bvecs for dwi files

    Input
    =====
    in_files:
        List of nifty files that are being merged.
    output_file_base:
        outputname with path and without extension
    """
    output_bval = output_file_base + ".bval"
    output_bvec = output_file_base + ".bvec"

    # bval
    with open(output_bval,'w') as bval_file:
        bvals = []
        for in_file in in_files:
            with open(in_file.replace('.nii.gz','.bval'),'r') as bval_in:
                bvals.append(bval_in.read().strip())
        bval_file.write(" ".join(bvals)+"\n")

    # bvec
    bvec_arrays = np.array([])
    i = 0
    for in_file in in_files:
        bvec_array = np.loadtxt(fname=in_file.replace('.nii.gz','.bvec'))
        if i == 0:
            bvec_arrays = bvec_array
        else:
            bvec_arrays = np.hstack((bvec_arrays,bvec_array))
        i = i + 1
    np.savetxt(output_bvec,bvec_arrays)