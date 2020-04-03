#!/bin/env python

import os
import copy

from argparse import ArgumentParser
from argparse import ArgumentDefaultsHelpFormatter

# own functions
import utils
import workflows
import outputs
import report.reports

from _version import get_versions

application_name = "dmri_preprocessing"
version = "0.0.2-1"

# Modified from qsiprep
def get_parser():
    """Build parser object"""
    #from ..__about__ import __version__

    verstr = application_name+' v{}'.format(version)

    parser = ArgumentParser(
        description=application_name+': dMRI preprocessing.',
        formatter_class=ArgumentDefaultsHelpFormatter)

    # Arguments as specified by BIDS-Apps
    # required, positional arguments
    # IMPORTANT: they must go directly with the parser object
    parser.add_argument('bids_dir',
                        type=str,
                        action='store',
                        help='the root folder of a BIDS valid dataset (sub-XXXXX folders '
                        'should be found at the top level in this folder).')
    parser.add_argument('output_dir',
                        action='store',
                        type=str,
                        help='the output path for the outcomes of preprocessing and visual'
                        ' reports')
    parser.add_argument('analysis_level',
                        choices=['participant'],
                        action='store',
                        help='processing stage to be run, only "participant" in the case of '
                        +application_name+' (see BIDS-Apps specification).')

    # optional arguments
    parser.add_argument('-v','--version', action='version', version=verstr)

    g_bids = parser.add_argument_group('Options for filtering BIDS queries')
    g_bids.add_argument(
        '--participant_label',
        '--participant-label',
        action='store',
        help='a single subject identifier (the sub- prefix can be removed)')
    g_bids.add_argument(
        '--session_label',
        '--session-label',
        action='store',
        help='a single session identifier (the ses- prefix can be removed)')
        
    g_perfm = parser.add_argument_group('Options to handle performance')
    g_perfm.add_argument(
        '--n_cpus',
        '--n-cpus',
        '--nthreads',
        action='store',
        default=1,
        type=int,
        help='maximum number of threads across all processes')

    g_conf = parser.add_argument_group('Workflow configuration')
    g_conf.add_argument(
        '--b0-threshold', '--b0_threshold',
        action='store',
        type=int,
        default=100,
        help='any value in the .bval file less than this will be considered '
        'a b=0 image. Current default threshold = 100; this threshold can be '
        'lowered or increased. Note, setting this too high can result in inaccurate results.')
    g_conf.add_argument(
        '--dwi_denoise_window', '--dwi-denoise-window',
        action='store',
        type=int,
        default=5,
        help='window size in voxels for ``dwidenoise``. Must be odd. '
             'If 0, ``dwidwenoise`` will not be run')
    #g_conf.add_argument(
    #    '--unringing-method', '--unringing-method',
    #    action='store',
    #    choices=['none', 'mrdegibbs'],
    #    help='Method for Gibbs-ringing removal.\n - none: no action\n - mrdegibbs: '
    #         'use mrdegibbs from mrtrix3')
    #g_conf.add_argument(
    #    '--dwi-no-biascorr', '--dwi_no_biascorr',
    #    action='store_true',
    #    help='skip b0-based dwi spatial bias correction')

    g_other = parser.add_argument_group('Other options')
    g_other.add_argument(
        '-w',
        '--work-dir', '--work_dir',
        type=str,
        action='store',
        help='path where intermediate results should be stored')

    return parser

opts = get_parser().parse_args()

BIDS_DIR = opts.bids_dir
OUTPUT_DIR = opts.output_dir
WORK_DIR = opts.work_dir

subject = opts.participant_label.replace("sub-","")
session = opts.session_label.replace("ses-","")


# Settings
b0_threshold = opts.b0_threshold
n_cpus = opts.n_cpus
denoise_filter_length = (
    opts.dwi_denoise_window,
    opts.dwi_denoise_window,
    opts.dwi_denoise_window
)

bids_input = os.path.join(BIDS_DIR,"sub-"+subject,"ses-"+session)
assert os.path.exists(bids_input) == True, "Input dir: %s does not exist." % bids_input

subject_work_dir = os.path.join(WORK_DIR, application_name + "_wf","sub-"+str(subject)+"_ses-"+str(session)+"_wf")
os.makedirs(subject_work_dir,exist_ok=True)

# Get overview of data
layout, subject_data = utils.get_bids_layout(BIDS_DIR,subject,session)
data = utils.get_overview_of_data(subject_data, layout, b0_threshold)

data_raw = copy.deepcopy(data)
data_raw['bids_dir'] = BIDS_DIR
data_raw['subject'] = subject
data_raw['session'] = session
data_raw['denoise_filer_length'] = denoise_filter_length
data_raw['fsl_version'] = workflows.get_fsl_version()
data_raw['mrtrix3_version'] = workflows.get_mrtrix3_version()
data_raw['ants_version'] = workflows.get_ants_version()
data_raw['application_version'] = version

# 00_pre_hmc, here we will make the following:
# - input dwi: sub-id_ses-id_dwi.nii.gz
# - input bvals and bvecs: sub-id_ses-id_dwi.[bvec,bval]
# - All input needed for head motion correcton (hmc)
pre_hmc_dir = os.path.join(subject_work_dir,'00_pre_hmc')
os.makedirs(pre_hmc_dir,exist_ok=True)

workflows.gather_inputs(data,subject,session,pre_hmc_dir)

figures = []

# mrtrix3 dwidenoise
output_svg = workflows.run_dwidenoise(data,denoise_filter_length,n_cpus,pre_hmc_dir)
figures.extend(output_svg)

# mrtrix3 mrdegibbs
# Only run mrdegibbs if we have acquired full k-space data:
if data['dwi'][0]['metadata']['PartialFourier'] == 1:
    output_svg = workflows.run_mrdegibbs(data,n_cpus,pre_hmc_dir)
    figures.extend(output_svg)

# Check if and how we should do topup
topup_options, phase_encoding_directions = utils.check_if_dataset_compatible_with_topup(data)

data_raw['topup_options'] = topup_options
data_raw['phase_encoding_directions'] = phase_encoding_directions

# topup
if topup_options['do_topup']:
    output_svg = workflows.run_topup(data,topup_options,pre_hmc_dir)
    figures.append(output_svg)

# eddy
eddy_inputs = workflows.prepare_eddy(data,topup_options,phase_encoding_directions,pre_hmc_dir)
eddy_inputs['in_file'] = data['dwi'][0]['filename']
eddy_inputs['in_bval'] = data['in_bval']
eddy_inputs['in_bvec'] = data['in_bvec']
eddy_output_dir = workflows.run_eddy(eddy_inputs,topup_options,subject_work_dir,n_cpus)

eddy_output = {}
data['dwi'][0]['filename'] = os.path.join(eddy_output_dir,'eddy_corrected.nii.gz')
eddy_output['rotated_bvec'] = os.path.join(eddy_output_dir,"eddy_corrected.eddy_rotated_bvecs")
eddy_output['cnr_maps'] = os.path.join(eddy_output_dir,"eddy_corrected.eddy_cnr_maps.nii.gz")

# N4biasfield correction!
output_svg = workflows.run_n4biasfieldcorrection(data,subject_work_dir)
figures.extend(output_svg)

# dtifit
dtifit_output_dir = workflows.run_dtifit(data['dwi'][0]['filename'],data['in_bval'],eddy_output['rotated_bvec'], eddy_inputs['in_mask'],subject_work_dir)

print("Output results to derivatives directory")
outputs.to_derivatives(data, data_raw,OUTPUT_DIR,application_name,eddy_output_dir,dtifit_output_dir,eddy_inputs,figures)

# Create report
report.reports.create_report(data, data_raw, OUTPUT_DIR, application_name)