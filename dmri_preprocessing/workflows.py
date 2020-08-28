#!/bin/env python
# Purpose: Gather all workflow routines here

import os
import shutil
import glob
import numpy as np

import nipype.pipeline.engine as pe 

from nipype.interfaces import fsl
from nipype.interfaces import mrtrix3
from nipype.interfaces import ants
from report.plots import plot_before_after_svg
import subprocess
import nibabel as nib

import utils

def get_fsl_version():
    """
    Get fsl version installed on machine which nipype is using.
    """
    return fsl.Info.version()

def get_mrtrix3_version():
    """
    Returns the version number of mrtrix3. 
    
    Might not work for all versions?
    """
    cmd = subprocess.run(["dwidenoise", "-version"], shell=True, capture_output=True)
    version = cmd.stdout.decode().split("\n")[0].split(",")[1].replace("version","")
    return version

def get_ants_version():
    """
    Returns the version number of mrtrix3. 
    
    Might not work for all versions?
    """
    cmd = subprocess.run(["antsRegistration -v"], shell=True, capture_output=True)
    version = cmd.stdout.decode().split("\n")[1].split(" ")[-1]
    return version

def gather_inputs(data, subject,session,output_dir):
    """
    Gathers the dwi data for processing. Places it in the work 
    directory. 
    
    If it exists more than one dwi sequence, they will be 
    merged if they have same phase encoding direction.

    Inputs
    ======
    data: dict with information about the data we are going to process.

    Outputs
    =======
    data: updated dict with information about the data we are going to
          process.
    """
    # Merge dwi data if more than one dwi file,
    # if not, copy the original data
    if len(data['dwi']) > 1:
        in_files_dwi = []
        encoding_directions = []
        i = 0
        for dwi in data['dwi']:
            encoding_direction = dwi['metadata']['PhaseEncodingDirection']
            # only merge data with same encoding direction
            if i > 0 and encoding_direction not in encoding_directions:
                continue
            encoding_directions.append(encoding_direction)
            in_files_dwi.append(dwi['filename'])
            # merge metadata
            # metadata fields that needs to be merged:
            # - 'ProtocolName','SAR','SeriesNumber','WipMemBlock'
            if i > 0:
                for label in ['ProtocolName','SAR','SeriesNumber','WipMemBlock']:
                    data['dwi'][0]['metadata'][label] = str(data['dwi'][0]['metadata'][label]) + "," + \
                    str(data['dwi'][i]['metadata'][label])
                del[data['dwi'][i]]
            i += 1

        output_file = os.path.join(output_dir,"sub-"+str(subject)+"_ses-"+str(session)+"_dwi.nii.gz")
        merge = pe.Node(
            fsl.Merge(
                dimension='t',
                in_files=in_files_dwi,
                merged_file=output_file,
                output_type="NIFTI_GZ"
            ),
            name='merge'
        )
        merge.base_dir = output_dir
        merge.run()
        utils.merge_bval_bvecs(in_files_dwi,output_file.replace('.nii.gz',''))
        data['dwi'][0]['filename'] = os.path.join(output_dir,output_file)
    else:
        shutil.copy(data['dwi'][0]['filename'],output_dir)
        shutil.copy(data['dwi'][0]['filename'].replace('.nii.gz','.bvec'),output_dir)
        shutil.copy(data['dwi'][0]['filename'].replace('.nii.gz','.bval'),output_dir)
        data['dwi'][0]['filename'] = os.path.join(output_dir,os.path.basename(data['dwi'][0]['filename']))
    
    # bval and bvecs
    data['in_bval'] = data['dwi'][0]['filename'].replace('.nii.gz','.bval')
    data['in_bvec'] = data['dwi'][0]['filename'].replace('.nii.gz','.bvec')

    # Make mask for qc plots
    mask_name = extract_mask_from_dwi(data,data['dwi'][0]['filename'])
    data['b0_mask'] = mask_name
    
    return data

def run_dwidenoise(data, denoise_filter_length, n_cpus, output_dir):
    """
    Run mrtrix3 dwidenoise routine on in_file

    Inputs
    ======
    data: dict containing information about data
    denoise_filter_length: tuple with 3 ints, e.g: (7,7,7)
    n_cpus: number of cpus
    output_dir: Output destination of work files.

    Outputs
    =======
    None
    """
    in_file = data['dwi'][0]['filename']
    out_dwidenoise = in_file.replace('.nii.gz','_denoised.nii.gz')
    dwidenoise = pe.Node(mrtrix3.preprocess.DWIDenoise(
            in_file=in_file,
            extent=denoise_filter_length,
            nthreads=n_cpus,
            out_file=out_dwidenoise           
        ), 
        name='dwidenoise'
    )
    dwidenoise.base_dir = output_dir
    dwidenoise.run()
    data['dwi'][0]['filename'] = out_dwidenoise

    # Produce qc figure
    output_svg_basename = out_dwidenoise.replace('.nii.gz','')
    # Extract high and low b0 value for qc report
    dwi_b_low = extract_frame_dwi(in_file,data['dwi'][0]['b0_idx'][0])
    dwi_b_high = extract_frame_dwi(in_file,data['dwi'][0]['bhigh_idx'][0])
    dwi_denoise_b_low = extract_frame_dwi(out_dwidenoise,data['dwi'][0]['b0_idx'][0])
    dwi_denoise_b_high = extract_frame_dwi(out_dwidenoise,data['dwi'][0]['bhigh_idx'][0])

    output_svg = [output_svg_basename + '_lowb.svg',output_svg_basename + '_highb.svg']
    plot_before_after_svg(dwi_b_low,dwi_denoise_b_low,data['b0_mask'],output_svg[0])
    plot_before_after_svg(dwi_b_high,dwi_denoise_b_high,data['b0_mask'],output_svg[1])

    return output_svg

def run_mrdegibbs(data, n_cpus, output_dir):
    """
    Run mrtrix3 dwidenoise routine on in_file

    Inputs
    ======
    data: dict containing information about data
    n_cpus: number of cpus
    output_dir: Output destination of work files.

    Outputs
    =======
    None
    """
    in_file = data['dwi'][0]['filename']
    out_mrdegibbs = in_file.replace('.nii.gz','_mrdegibbs.nii.gz')
    mrdegibbs = pe.Node(mrtrix3.MRDeGibbs(
            in_file=in_file,
            out_file=out_mrdegibbs,
            nthreads=n_cpus
        ), 
        name='mrdegibbs'
    )
    mrdegibbs.base_dir = output_dir
    mrdegibbs.run()

    data['dwi'][0]['filename'] = out_mrdegibbs

    # Produce qc figure
    output_svg_basename = out_mrdegibbs.replace('_denoised','').replace('.nii.gz','')
    print(output_svg_basename)

    # Extract high and low b0 value for qc report
    dwi_b_low = extract_frame_dwi(in_file,data['dwi'][0]['b0_idx'][0])
    dwi_b_high = extract_frame_dwi(in_file,data['dwi'][0]['bhigh_idx'][0])
    dwi_degibbs_b_low = extract_frame_dwi(out_mrdegibbs,data['dwi'][0]['b0_idx'][0])
    dwi_degibbs_b_high = extract_frame_dwi(out_mrdegibbs,data['dwi'][0]['bhigh_idx'][0])

    output_svg = [output_svg_basename + '_lowb.svg',output_svg_basename + '_highb.svg']
    plot_before_after_svg(dwi_b_low,dwi_degibbs_b_low,data['b0_mask'],output_svg[0])
    plot_before_after_svg(dwi_b_high,dwi_degibbs_b_high,data['b0_mask'],output_svg[1])

    return output_svg

def run_topup(data, topup_options, output_dir):
    """
    Run fsl topup routine on data.

    Inputs
    ======
    data: dict containing datasets and metainformation.
    topup_options: dict containing info on how to apply topup
    output_dir: output destination of work files.

    Outputs
    =======
    output_svg_name: file path to svg containing before and after of sdc
    """

    # topup: preparation
    in_files_fmap = []
    encoding_directions = []
    readout_times = []

    if topup_options['only_sbref']:
        for sbref in data['sbref']:
            in_files_fmap.append(sbref['filename'])
            encoding_directions.append(sbref['metadata']['PhaseEncodingDirection'])
            readout_times.append(sbref['metadata']['TotalReadoutTime'])

    elif topup_options['only_fmap']:
        # merge fmaps:
        for fmap in data['fmap']:
            in_files_fmap.append(fmap['filename'])
            # Add as many entries to the encoding direction file as it is frames
            # in the nifty files
            fmap_nii_frames = nib.load(fmap['filename']).shape[3]
            for i in range(0,fmap_nii_frames):
                encoding_directions.append(fmap['metadata']['PhaseEncodingDirection'])
                readout_times.append(fmap['metadata']['TotalReadoutTime'])
                
    elif topup_options['dwi_fmap_combined']:
        # Extract b0 from dwi
        b0_file = extract_frame_dwi(data['dwi'][0]['filename'],data['dwi'][0]['b0_idx'][0])

        in_files_fmap.append(b0_file)
        encoding_directions.append(data['dwi'][0]['metadata']['PhaseEncodingDirection'])
        readout_times.append(data['dwi'][0]['metadata']['TotalReadoutTime'])

        # fmaps
        for fmap in data['fmap']:
            in_files_fmap.append(fmap['filename'])
            encoding_directions.append(fmap['metadata']['PhaseEncodingDirection'])
            readout_times.append(fmap['metadata']['TotalReadoutTime'])

    multiple_encoding_directions_file = os.path.join(output_dir,"AP_PA.nii.gz")
    merge = pe.Node(
        fsl.Merge(
            dimension='t',
            in_files=in_files_fmap,
            merged_file=multiple_encoding_directions_file,
            output_type="NIFTI_GZ"
        ), 
        name='merge'
    )
    merge.base_dir = output_dir
    merge.run()

    topup_nipype_name = 'topup'
    topup = pe.Node(
        fsl.TOPUP(
            in_file=multiple_encoding_directions_file, 
            encoding_direction=encoding_directions, 
            readout_times=readout_times,
            output_type = "NIFTI_GZ"
        ),
        name=topup_nipype_name
    )
    topup.base_dir = output_dir
    topup.run()

    # Produce qc figure
    before_nii = extract_frame_dwi(multiple_encoding_directions_file,0)
    after_nii_basename = os.path.basename(multiple_encoding_directions_file.replace('.nii.gz','_corrected.nii.gz'))
    after_nii = extract_frame_dwi(os.path.join(output_dir,topup_nipype_name,after_nii_basename),0)
    output_svg_name = after_nii.replace('.nii.gz','.svg')

    plot_before_after_svg(before_nii,after_nii,data['b0_mask'],output_svg_name)

    return output_svg_name

def extract_frame_dwi(fname,frame_nr):
    """
    Extracts frame from dwi file

    Input
    =====
    fname: full path to dwi file
    frame_nr: frame number to extract. 0 extracts the first frame.

    Output
    ======
    output: full path of file with extracted frame
    """
    # Extracts frame from fname
    output = fname.replace('.nii.gz','_%02i.nii.gz' % frame_nr)
    if not os.path.exists(output):
        extract = pe.Node(
            fsl.ExtractROI(
                in_file=fname,
                t_min=frame_nr,
                t_size=1,roi_file=output,
                output_type="NIFTI_GZ"
            ), 
            name='extract_%02i' % frame_nr
        )
        extract.base_dir = os.path.dirname(fname)
        extract.run()

    return output

def extract_mask_from_dwi(data,dwi_file):
    """
    Extracts mask from first b0 volumne in dwi_file

    Input
    =====
    data:
        dict with data information.
    dwi_file:
        dwi file where mask of b0 is to be extracted.

    Output
    ======
    in_mask:
        path to mask that were created.
    """
    # Create mask from b0
    b0_file = extract_frame_dwi(dwi_file,data['dwi'][0]['b0_idx'][0])

    out_brain = b0_file.replace('.nii.gz','_brain.nii.gz')
    in_mask = out_brain.replace('.nii.gz','_mask.nii.gz')
    bet = pe.Node(
        fsl.BET(
            in_file=b0_file,
            mask=True,
            frac=0.3,
            out_file=out_brain,
            output_type="NIFTI_GZ"
        ),
        name='bet'
    )
    bet.base_dir = os.path.dirname(dwi_file)
    bet.run()

    return in_mask

def prepare_eddy(data,topup_options,phase_encoding_directions,output_dir):
    """
    Prepare inputs for fsl eddy routine.

    Inputs
    ======
    data: dict with information about the data
    topup_options: dict containing info on how to apply topup
    phase_encoding_directions: dict with phase encoding directions for data.
    output_dir: output destination of work files.

    Outputs
    =======
    eddy_inputs: dict with eddy_inputs
    """
    # For eddy, we need:
    # - in_file: our dwi file
    # - in_mask: mask around head
    # - in_index: file containing indeces for all volumes
    # - in_acqp: File containing acquisition parameters
    # - in_bvec: File containing the b-vectors for all volumes in --imain
    # - in_bval:File containing the b-values for all volumes in --imain
    # 
    # If topup is done:
    # - in_topup_fieldcoef:
    # - in_topup_movpar:

    in_acqp_idx = 1
    eddy_inputs = {}

    in_file = data['dwi'][0]['filename']

    if topup_options['do_topup']:
        # If we have done topup, we have the in_acqp file, as well as other inputs required by eddy
        topup_basename = os.path.join(output_dir,"topup","AP_PA")
        eddy_inputs['in_acqp'] = topup_basename + '_encfile.txt'
        eddy_inputs['in_topup_fieldcoef'] = topup_basename + "_base_fieldcoef.nii.gz"
        eddy_inputs['in_topup_movpar'] = topup_basename + "_base_movpar.txt"
        eddy_inputs['in_topup_corrected'] = topup_basename + "_corrected.nii.gz"

        # Make mask out of the corrected fmaps
        in_mean_topup_corrected = eddy_inputs['in_topup_corrected'].replace("_corrected.nii.gz","_corrected_mean.nii.gz")
        mean = pe.Node(
            fsl.maths.MathsCommand(
                in_file=eddy_inputs['in_topup_corrected'],
                args="-Tmean",
                out_file=in_mean_topup_corrected,
                output_type="NIFTI_GZ"
            ), 
            name='mean'
        )
        mean.base_dir = output_dir
        mean.run()

        out_brain = in_mean_topup_corrected.replace("_mean.nii.gz","_mean_brain.nii.gz")
        eddy_inputs['in_mask'] = out_brain.replace('_brain.nii.gz','_brain_mask.nii.gz')
        bet = pe.Node(
            fsl.BET(
                in_file=in_mean_topup_corrected,
                mask=True,
                frac=0.3, # Higher values can remove parts of brain.
                out_file=out_brain,
                output_type="NIFTI_GZ"
            ),
            name='bet'
        )
        bet.base_dir = output_dir
        bet.run()

        # Check if the dwi brain mask and the brain mask extracted
        # from the topup corrected data have the same geometry.
        fmap_corr_brain_mask_img = nib.load(eddy_inputs['in_mask'])
        dwi_brain_mask_img = nib.load(data['b0_mask'])

        # Extracts voxel dimensions
        fmap_corr_voxels = fmap_corr_brain_mask_img.header.get_zooms()
        dwi_voxels = dwi_brain_mask_img.header.get_zooms()

        diff_per = np.abs(np.mean(np.array(fmap_corr_voxels)/np.array(dwi_voxels))-1)

        if fmap_corr_voxels != dwi_voxels and diff_per < 1e-04:
            # Change input mask
            input_mean_topup_mask = eddy_inputs['in_mask']
            copygeom = pe.Node(
                fsl.utils.CopyGeom(
                    in_file=data['b0_mask'],
                    dest_file=input_mean_topup_mask,
                    output_type="NIFTI_GZ"
                ), 
                name='copygeom'
            )
            copygeom.base_dir = output_dir
            copygeom.run()

            eddy_inputs['in_mask'] = input_mean_topup_mask.replace("/topup/","/copygeom/")

        # Check if first file in acq_p file is corresponding to the same phase encoding directions as the dwi file
        if topup_options['only_fmap']:
            for i in range(0,len(phase_encoding_directions['fmap'])):
                if phase_encoding_directions['fmap'][i] == phase_encoding_directions['dwi'][0]:
                    in_acqp_idx = 1+i
        elif topup_options['only_sbref']:
            for i in range(0,len(phase_encoding_directions['sbref'])):
                if phase_encoding_directions['sbref'][i] == phase_encoding_directions['dwi'][0]:
                    in_acqp_idx = i+1

        elif topup_options['dwi_fmap_combined']:
            in_acqp_idx = 1
        
    else:
        # If topup is not ran, we need to create:
        # - acquisition parameter file
        # - mask from b0, instead of corrected fieldmaps
        eddy_inputs['in_mask'] = data['b0_mask']
        # Create acqp_file
        eddy_inputs['in_acqp'] = in_file.replace('.nii.gz','_acq_param.txt')

        phase_encoding_direction = data['dwi'][0]['metadata']['PhaseEncodingDirection']
        total_readout_time = data['dwi'][0]['metadata']['TotalReadoutTime']
        with open(eddy_inputs['in_acqp'],'w') as acqp_file:
            if phase_encoding_direction == 'x-':
                acqp_file.write("-1 0 0 "+str(total_readout_time)+"\n")
            elif phase_encoding_direction == 'x':
                acqp_file.write("1 0 0 "+str(total_readout_time)+"\n")
            elif phase_encoding_direction == 'y-':
                acqp_file.write("0 -1 0 "+str(total_readout_time)+"\n")
            elif phase_encoding_direction == 'y':
                acqp_file.write("0 1 0 "+str(total_readout_time)+"\n")
            elif phase_encoding_direction == 'z':
                acqp_file.write("0 0 1 "+str(total_readout_time)+"\n")
            elif phase_encoding_direction == 'z-':
                acqp_file.write("0 0 -1 "+str(total_readout_time)+"\n")

    # Make in_index file
    eddy_inputs['in_index'] = in_file.replace('.nii.gz','_index.txt')
    in_bval = data['in_bval']
    with open(in_bval, 'r') as bval_file:
        bvals = bval_file.read().strip().split(" ")

    in_acqp_indeces = []
    for bval in bvals:
        in_acqp_indeces.append(str(in_acqp_idx))

    with open(eddy_inputs['in_index'],'w') as index_file:
        index_file.write(" ".join(in_acqp_indeces)+"\n")
    
    return eddy_inputs

def run_eddy(eddy_inputs,topup_options,output_dir,n_cpus):
    """
    Run eddy.

    Inputs
    ======
    topup_options: dict containing info on how to apply topup
    eddy_inputs: dict with inputs to eddy.
    output_dir: output destination of work files.

    Outputs
    =======
    eddy_work_dir: eddy work directory
    """
    name = '01_hmc'

    if topup_options['do_topup']:
        eddy = pe.Node(
            fsl.Eddy(
                in_file = eddy_inputs['in_file'],
                in_bval = eddy_inputs['in_bval'],
                in_bvec = eddy_inputs['in_bvec'],
                in_mask = eddy_inputs['in_mask'],
                in_acqp = eddy_inputs['in_acqp'],
                in_index = eddy_inputs['in_index'],
                in_topup_fieldcoef = eddy_inputs['in_topup_fieldcoef'],
                in_topup_movpar = eddy_inputs['in_topup_movpar'],
                cnr_maps = True,
                repol = True,
                num_threads = n_cpus,
                output_type = "NIFTI_GZ"
            ),
            name=name
        )
        eddy.base_dir = output_dir
        eddy.run()
    else:
        eddy = pe.Node(
            fsl.Eddy(
                in_file = eddy_inputs['in_file'],
                in_bval = eddy_inputs['in_bval'],
                in_bvec = eddy_inputs['in_bvec'],
                in_mask = eddy_inputs['in_mask'],
                in_acqp = eddy_inputs['in_acqp'],
                in_index = eddy_inputs['in_index'],
                cnr_maps = True,
                repol = True,
                num_threads = n_cpus,
                output_type = "NIFTI_GZ"
            ),
            name=name
        )
        eddy.base_dir = output_dir
        eddy.run()
    return os.path.join(output_dir,name)

def run_n4biasfieldcorrection(data,output_dir):
    """
    Run ants biasfieldcorrection.

    This method estimates the bias field correction on one b0 image,
    then applies it on the full sequence by division using fslmaths.

    Inputs
    ======
    in_file: input dwi sequence to correct. Must contain a b0 volume
    output_dir: work directory for nipype

    Outputs
    =======
    dtifit_work_dir: eddy work directory
    """

    # Generate bias field
    dwi_b0 = extract_frame_dwi(data['dwi'][0]['filename'],data['dwi'][0]['b0_idx'][0])
    bias_field_output = "bias_field_b0.nii.gz"

    name_n4bias = '02_n4biasfieldcorrection'
    # Run dtifit on output
    n4bias = pe.Node(
        ants.N4BiasFieldCorrection(
            input_image = dwi_b0,
            save_bias = True,
            copy_header = False,
            bias_image = bias_field_output
        ),
        name=name_n4bias
    )
    n4bias.base_dir = output_dir
    n4bias.run()

    # Apply bias field on dwi sequence by division using fslmaths
    name_apply_field = 'apply_bias_field'
    out_bias = data['dwi'][0]['filename'].replace('.nii.gz','_bias_corrected.nii.gz')
    base_dir = os.path.join(output_dir,name_n4bias)

    apply_field = pe.Node(
        fsl.maths.BinaryMaths(
            in_file = data['dwi'][0]['filename'],
            operation = 'div',
            operand_file = os.path.join(base_dir,bias_field_output),
            out_file = out_bias,
            output_type = "NIFTI_GZ"
        ),
        name=name_apply_field
    )
    apply_field.base_dir = base_dir
    apply_field.run()

    # Produce qc figures
    output_svg_basename = out_bias.replace('.nii.gz','')
    # Extract high and low b0 value for qc report
    dwi_b_low = extract_frame_dwi(data['dwi'][0]['filename'],data['dwi'][0]['b0_idx'][0])
    dwi_b_high = extract_frame_dwi(data['dwi'][0]['filename'],data['dwi'][0]['bhigh_idx'][0])
    dwi_denoise_b_low = extract_frame_dwi(out_bias,data['dwi'][0]['b0_idx'][0])
    dwi_denoise_b_high = extract_frame_dwi(out_bias,data['dwi'][0]['bhigh_idx'][0])

    output_svg = [output_svg_basename + '_lowb.svg',output_svg_basename + '_highb.svg']
    plot_before_after_svg(dwi_b_low,dwi_denoise_b_low,data['b0_mask'],output_svg[0])
    plot_before_after_svg(dwi_b_high,dwi_denoise_b_high,data['b0_mask'],output_svg[1])

    data['dwi'][0]['filename'] = out_bias

    return output_svg

def run_dtifit(in_file,in_bval,in_bvec,in_mask,output_dir):
    """
    Run FSLs dtifit.

    Inputs
    ======
    in_file: input file to fit diffusion tensor
    in_bval: bval file
    in_bvec: bvec file
    in_mask: brain mask file
    output_dir: work directory for nipype

    Outputs
    =======
    dtifit_work_dir: dtifit work directory
    """
    name = '03_dtifit'
    # Run dtifit on output
    dtifit = pe.Node(
        fsl.DTIFit(
            dwi = in_file,
            bvals = in_bval,
            bvecs = in_bvec,
            mask = in_mask,
            output_type = "NIFTI_GZ"
        ),
        name=name
    )
    dtifit.base_dir = output_dir
    dtifit.run()

    return os.path.join(output_dir,name)

def run_rd(dtifit_output_dir):
    """
    Calculate radial diffusitivity (RD). 
    RD = (L2 + L3) / 2.

    Outputs to the same directory as dtifit.

    Inputs
    ======
    dtifit_output_dir: output directory of FSLs dtifit
    """
    l2_file = glob.glob(os.path.join(dtifit_output_dir,"*L2*.nii.gz"))[0]
    l3_file = glob.glob(os.path.join(dtifit_output_dir,"*L3*.nii.gz"))[0]
    output_file = l2_file.replace("L2","RD")

    fsl_rd = pe.Node(
        fsl.MultiImageMaths(
            in_file=l2_file,
            op_string="-add %s -div 2",
            operand_files=l3_file,
            out_file=output_file,
            output_type="NIFTI_GZ"
        ), 
        name='fslmaths'
    )
    fsl_rd.base_dir = dtifit_output_dir
    fsl_rd.run()