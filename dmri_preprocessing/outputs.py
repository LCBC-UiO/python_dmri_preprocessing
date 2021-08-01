#!/usr/bin/env python
# Purpose: Handle the transfer from work dir to derivatives

import shutil
import os
import numpy as np
import pandas as pd
import json
import glob

from dmri_preprocessing.report.plots import plot_dMRI_confounds_carpet, plot_gradients

def create_confounds_tsv(output_dir_dwi,sub_ses_basename,eddy_output_dir,eddy_input):
    """
    Creates a .tsv file with different estimations and statistics done during the 
    processing.

    Input
    =====
    output_dir_dwi:
        full path to dwi output dir for this subject and session
    sub_ses_basename:
        basename of data output prefix
    eddy_output_dir:
        path to eddy work directory during processing
    eddy_input:
        dict containing information about input datasets to eddy.

    Output
    ======
    confound_derivatives:
        path to created .tsv file containing estimations and statistics
    """
    # confounds.tsv
    confound_derivatives = os.path.join(output_dir_dwi,sub_ses_basename+"confounds.tsv")
    files_to_extract_data = [os.path.join(eddy_output_dir,"eddy_corrected.eddy_movement_rms"),
                            os.path.join(eddy_output_dir,"eddy_corrected.eddy_restricted_movement_rms"),
                            os.path.join(eddy_output_dir,"eddy_corrected.eddy_parameters"),
                            eddy_input['in_bval']]

    columns = [
        'eddy_movement_rms_relative_to_first',
        'eddy_movement_rms_relative_to_previous',
        'eddy_restricted_movement_rms_relative_to_first',
        'eddy_restricted_movement_rms_relative_to_previous',
        'trans_x',
        'trans_y',
        'trans_z',
        'rot_x',
        'rot_y',
        'rot_z',
        'bval'
    ]
    i = 0
    # merge data
    for file_eddy in files_to_extract_data:
        data_file = np.loadtxt(fname=file_eddy)
        if 'eddy_parameters' in file_eddy:
            data_file = data_file[:,0:6]
        elif 'bval' in file_eddy:
            data_file = np.array(np.matrix(data_file).T)
        if i == 0:
            data = data_file
        else:
            data = np.hstack((data,data_file))
        i += 1

    # Use panda to save as tsv
    df = pd.DataFrame(data=data,columns=columns)
    df.to_csv(confound_derivatives, sep="\t",index=False)

    return confound_derivatives

def create_dataset_description(data_raw,output_dir,application_name):
    """
    Create dataset_description.json according to bids standard.
    """
    dataset_description = {
        "Name": application_name +" outputs",
        "BIDSVersion": "TODO: Fill out",
        "PipelineDescription": {
            "Name": application_name,
            "Version": data_raw['application_version'],
            "CodeURL": "https://github.com/LCBC-UiO/python_dmri_preprocessing/archive/"+data_raw['application_version']+'.tar.gz'
            },
        "CodeURL":"https://github.com/LCBC-UiO/python_dmri_preprocessing",
        "SourceDatasets": [
            {
                "Path": "TODO: Fill in path",
                "Version": "TODO: Fill in version"
            }
        ]
    }
    filename = os.path.join(output_dir,"dataset_description.json")

    if not os.path.exists(filename):
        with open(filename,'w') as json_file:
            json_file.write(json.dumps(dataset_description, sort_keys=True, indent=4, separators=(',', ': ')))

def to_derivatives(data, data_raw, derivatives_dir, application_name, eddy_output_dir, dtifit_dir, eddy_input, figures):
    """
    Copy all processed data from work directory to derivatives directory.

    Input
    =====
    data:
        dict containing processing information containing only datasets used in the processing,
        as well as filenames refering to the work directory, instead of orginal data.
    data_raw:
        dict containing processsing information containing all data, also the ones not used in
        the processing. Typically fieldmaps.
    derivatives_dir:
        path to data_out dir that user specified.
    application_name:
        name of the app
    eddy_output_dir:
        path to eddys work directory
    dtifit_dir:
        path to dtifits work directory
    eddy_input:
        dict containing inputs to eddy.
    figures:
        list of figure paths that will be copied to derivatives directory.
    """
    # Output data to bids/derivatives
    output_dir_base = os.path.join(derivatives_dir, application_name)
    sub = "sub-" + str(data_raw['subject'])
    ses = "ses-" + str(data_raw['session'])

    output_dir_session = os.path.join(output_dir_base,sub,ses)
    output_dir_dwi = os.path.join(output_dir_session,"dwi")
    output_dir_figures = os.path.join(output_dir_session,"figures")

    os.makedirs(output_dir_dwi,exist_ok=True)
    os.makedirs(output_dir_figures,exist_ok=True)
    
    # Create dataset_description.json
    create_dataset_description(data_raw,output_dir_base,application_name)

    sub_ses_basename = sub + "_" + ses + "_space-orig_desc-"

    # Outputs to take care of:
    eddy_output_dict = {
        'eddy_corrected.eddy_rotated_bvecs': sub_ses_basename + 'preproc_dwi.bvec',
        'eddy_corrected.eddy_cnr_maps.nii.gz': sub_ses_basename + 'preproc_cnr.nii.gz'
    }
    for eddy_output in eddy_output_dict:
        eddy_output_p = os.path.join(eddy_output_dir,eddy_output)
        eddy_derivative = os.path.join(output_dir_dwi,eddy_output_dict[eddy_output])
        shutil.copy(eddy_output_p,eddy_derivative)

    other_outputs_dict = {
        data['dwi'][0]['filename']: sub_ses_basename + 'preproc_dwi.nii.gz',
        eddy_input['in_bval']: sub_ses_basename + "preproc_dwi.bval",
        eddy_input['in_mask']: sub_ses_basename + "preproc_mask.nii.gz"
    }

    for other_output in other_outputs_dict:
        other_derivative = os.path.join(output_dir_dwi,other_outputs_dict[other_output])
        shutil.copy(other_output,other_derivative)

    # Create confounds tsv parameters.
    confounds_file = create_confounds_tsv(output_dir_dwi,sub_ses_basename,eddy_output_dir,eddy_input)

    # plot confounds
    sliceqc_file = os.path.join(eddy_output_dir,'eddy_corrected.eddy_outlier_n_sqr_stdev_map')
    output_confounds_fig = os.path.join(output_dir_figures,sub_ses_basename+"confounds_plot.svg")
    plot_dMRI_confounds_carpet(confounds_file,sliceqc_file,eddy_input['in_mask'],output_confounds_fig)

    # plot gradients 
    final_bvec = os.path.join(eddy_output_dir,'eddy_corrected.eddy_rotated_bvecs')
    output_bvecs_plot = os.path.join(output_dir_figures,sub_ses_basename+"bvecs_plot.gif")

    bvals = np.loadtxt(fname=eddy_input['in_bval']).T
    orig_bvecs = np.loadtxt(fname=eddy_input['in_bvec']).T
    source_filenums = np.ones_like(bvals)
    final_bvecs = np.loadtxt(fname=final_bvec).T

    plot_gradients(bvals, orig_bvecs, source_filenums, output_bvecs_plot, final_bvecs=final_bvecs,frames=80)

    # Copy over other figures:
    for figure in figures:
        output_name = ""
        # dwidenoise
        if "denoised" in figure:
            if "lowb" in figure:
                b_type = "low"
            else:
                b_type = "high"
            output_name = os.path.join(output_dir_figures,sub_ses_basename+"dwidenoise_b-"+b_type+"_plot.svg")
        # mrdegibbs
        elif "degibbs" in figure:
            if "lowb" in figure:
                b_type = "low"
            else:
                b_type = "high"
            output_name = os.path.join(output_dir_figures,sub_ses_basename+"degibbs_b-"+b_type+"_plot.svg")
        # N4biasfieldcorrection
        elif "bias_corrected" in figure:
            if "lowb" in figure:
                b_type = "low"
            else:
                b_type = "high"
            output_name = os.path.join(output_dir_figures,sub_ses_basename+"bias_corrected_b-"+b_type+"_plot.svg")
        # topup
        elif "AP_PA_corrected" in figure:
            output_name = os.path.join(output_dir_figures,sub_ses_basename+"sdc_plot.svg")
        shutil.copy(figure,output_name)
    
    # Copy dtifit data to derivatives directory
    for dtifit_file in glob.glob(os.path.join(dtifit_dir,"dtifit_*.nii.gz")):
        dtifit_basename = os.path.basename(dtifit_file)
        dtifit_derivative = dtifit_basename.replace(
            "dtifit__",
            sub_ses_basename+"preproc_model-DTI_parameter-"
        )
        dtifit_derivative = dtifit_derivative.replace(
            '.nii.gz',
            '_diffmodel.nii.gz'
        )
        dtifit_derivative_p = os.path.join(output_dir_dwi,dtifit_derivative)
        shutil.copy(dtifit_file, dtifit_derivative_p)

    # Create json files
    create_json(data_raw,os.path.join(output_dir_dwi,sub_ses_basename))

def get_raw_sources(data_raw):
    """
    Generate the raw data sources for which the derivate data
    originates from.

    Input
    =====
    data_raw:
        dict containing processing information
    
    Output
    ======
    raw_sources:
        list containing raw source data.
    """
    raw_sources = []
    for dwi in data_raw['dwi']:
        raw_sources.append(
            dwi['filename'].replace(data_raw['bids_dir'],'')
        )
    if data_raw['topup_options']['only_sbref'] == True:
        for sbref in data_raw['sbref']:
            raw_sources.append(
                sbref['filename'].replace(data_raw['bids_dir'],'')
            )
    else:
        for fmap in data_raw['fmap']:
            raw_sources.append(
                fmap['filename'].replace(data_raw['bids_dir'],'')
            )

    return raw_sources

def create_json(data_raw, sub_ses_basename_p):
    """
    Create metadata .json files which will accompany the final files
    in the derivatives directory.

    Writes _mask.json, _dwi.json and _diffmodel.json to sub/ses/dwi/
    directory.

    Input
    =====
    data_raw: 
        dict containing processing information
    sub_ses_basename_p: 
        prefix to dwi files containing full output path
    
    Output
    ======
    none

    But, generates the files described above.
    """
    
    raw_sources = get_raw_sources(data_raw)
    
    # mask.json
    mask_json_filename = sub_ses_basename_p + "preproc_mask.json"
    mask_json = {
        'RawSources': raw_sources,
        'Type': 'Brain',
        'SpatialReference':'orig'
    }
    # _dwi.json
    dwi_json_filename = sub_ses_basename_p + "preproc_dwi.json"
    dwi_json = {
        'RawSources': raw_sources,
        'SpatialReference':'orig',
        'SkullStripped':False,
        'Denoising':'mrtrix3 dwidenoise, filter: %s' % str(data_raw['denoise_filer_length']),
        'MotionCorrection':True,
        'EddyCurrentCorrection':True,
        'HMC model':'fsl eddy',
        'fsl version': data_raw['fsl_version'],
        'mrtrix3 version': data_raw['mrtrix3_version']
    }
    # _diffmodel.json
    diffmodel_json_filename = sub_ses_basename_p + "preproc_model-DTI_diffmodel.json"
    diffmodel_json = {
        'Parameters':{
            'FitMethod':'OLS'
        },
        'command':'dtifit',
        'fsl version': data_raw['fsl_version']
    }

    # write json files
    json_to_write = {
        mask_json_filename: mask_json,
        dwi_json_filename: dwi_json,
        diffmodel_json_filename: diffmodel_json
    }
    for json_filename in json_to_write:
        with open(json_filename,'w') as json_file:
            json_file.write(json.dumps(json_to_write[json_filename], sort_keys=True, indent=4, separators=(',', ': ')))
