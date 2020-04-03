#!/bin/env python
# Purpose: Handle the report generation, taken from fmriprep

from jinja2 import Environment, FileSystemLoader
import glob
import os

TEMPLATE_FILE = "report.tpl"
dirname = os.path.dirname(__file__)
#print(dirname)

templateLoader = FileSystemLoader(searchpath=dirname)
templateEnv = Environment(loader=templateLoader)
template = templateEnv.get_template(TEMPLATE_FILE)

def get_data_info(data_type):
    data_summary = ""
    n = len(data_type)
    i = 0
    for data in data_type:
        data_summary += os.path.basename(data['filename']) + " (dir: "+ data['metadata']['PhaseEncodingDirection']+")"
        # Add comma
        if i != (n-1):
            data_summary += ", "
        i += 1
    return data_summary

def create_report(data, data_raw, derivatives_dir, application_name):
    """
    Create .html report for all processing steps.
    """

    output_dir_base = os.path.join(derivatives_dir, application_name)
    sub = "sub-" + str(data_raw['subject'])
    ses = "ses-" + str(data_raw['session'])

    fsl_version = data_raw['fsl_version']
    mrtrix3_version = data_raw['mrtrix3_version']
    ants_version = data_raw['ants_version']
    application_version = data_raw['application_version']

    filter_length = data_raw['denoise_filer_length']

    topup = data_raw['topup_options']['do_topup']
    topup_inputs = []

    degibbs = False
    if data['dwi'][0]['metadata']['PartialFourier'] == 1:
        degibbs = True

    if data_raw['topup_options']['only_sbref'] == True:
        for sbref in data_raw['sbref']:
            topup_inputs.append(
                sbref['filename'].replace(data_raw['bids_dir'],'')
            )
    elif data_raw['topup_options']['only_fmap'] == True:
        for fmap in data_raw['fmap']:
            topup_inputs.append(
                fmap['filename'].replace(data_raw['bids_dir'],'')
            )
    else:
        for dwi in data_raw['dwi']:
            topup_inputs.append(
                dwi['filename'].replace(data_raw['bids_dir'],'')
            )
        for fmap in data_raw['fmap']:
            topup_inputs.append(
                fmap['filename'].replace(data_raw['bids_dir'],'')
            )

    summary = {
        'bullets':{
                'subject: ': sub,
                'session: ': ses,
        },
    }

    # Add data to summary:
    if len(data_raw['dwi']) != 0:
        summary['bullets']['dwi'] = get_data_info(data_raw['dwi'])
    if len(data_raw['fmap']) != 0:
        summary['bullets']['fmap'] = get_data_info(data_raw['fmap'])
    if len(data_raw['sbref']) != 0:
        summary['bullets']['sbref'] = get_data_info(data_raw['sbref'])

    sections = {
        'Denoising':{
            'Summary':{
                'bullets':{
                    'MP-PCA denoising': 'mrtrix3 dwidenoise: '+str(filter_length),
                    'Removal of Gibbs ringing artifacts': degibbs,
                },
            },
            'MP-PCA denoising':{
                'description': 'Effect of MP-PCA denoising on a low and high-b image.',
                'figures': [
                    ses + '/figures/' + sub + '_' + ses + '_space-orig_desc-dwidenoise_b-low_plot.svg',
                    ses + '/figures/' + sub + '_' + ses + '_space-orig_desc-dwidenoise_b-high_plot.svg'
                ]
            },
            'Removal of Gibbs ringing artifacts':{
                'description': 'Effect of Gibbs ringing artifacts removal (Kellner et. al, 2016) on a low and high-b image.',
                'figures': [
                    ses + '/figures/' + sub + '_' + ses + '_space-orig_desc-degibbs_b-low_plot.svg',
                    ses + '/figures/' + sub + '_' + ses + '_space-orig_desc-degibbs_b-high_plot.svg'
                ]
            }
        },
        'Diffusion':{
            'Summary':{
                'bullets':{
                    'Susceptibility distortion correction': topup,
                    'HMC model': 'fsl Eddy',
                },
            },
            'DWI Sampling Scheme':{
                'description': 'DWI sampling scheme.',
                'figures':[
                    ses + '/figures/' + sub + '_' + ses + '_space-orig_desc-bvecs_plot.gif'
                ]
            },
            'Susceptibility distortion correction':{
                'description': 'Susceptibility distortion correction.',
                'bullets':{
                    'method': 'fsl TOPUP',
                    'inputs to TOPUP': ", ".join(topup_inputs),
                },
                'figures': [
                    ses + '/figures/' + sub + '_' + ses + '_space-orig_desc-sdc_plot.svg'
                ]
            },
            'Bias field correction':{
                'description': 
                    'The bias field was estimated on one b0 image by ANTs N4Biasfieldcorrection.\
                    Then, the field was applied to the full dwi sequence by dividing the bias field using fslmaths. ',
                'bullets':{
                    'method': 'ANTs N4biasfieldcorrection, fslmaths.',
                },
                'figures': [
                    ses + '/figures/' + sub + '_' + ses + '_space-orig_desc-bias_corrected_b-low_plot.svg',
                    ses + '/figures/' + sub + '_' + ses + '_space-orig_desc-bias_corrected_b-high_plot.svg'
                ]
            },
            'DWI summary':{
                'description': 'Statistics from eddy are plotted. The \
                "carpet" plot is the output of eddy_outlier_n_sqr_stdev_map, \
                which, according to the <a href="https://fsl.fmrib.ox.ac.uk/fsl/fslwiki/eddy/UsersGuide#Understanding_eddy_output">FSL documentation</a> is: \
                "The numbers denote how many standard deviations off the square root of the mean squared difference between observation and prediction is."',
                'figures': [
                    ses + '/figures/' + sub + '_' + ses + '_space-orig_desc-confounds_plot.svg'
                ]
            }
        },
        'About':{
            'Versions': {
                'bullets':{
                    application_name + ' version': application_version,
                    'fsl version': fsl_version,
                    'mrtrix3 version': mrtrix3_version,
                    'ants version': ants_version
                }
            },
            'References':{
                'bullets':{
                    'Kellner, E; Dhital, B; Kiselev, V.G & Reisert, M. Gibbs-ringing artifact removal based on local subvoxel-shifts. Magnetic Resonance in Medicine, 2016, 76, 1574-1581'
                }
            }
        }
    }
    # Delete sections which are not relevant for subject
    if degibbs is False:
        del sections['Denoising']['Removal of Gibbs ringing artifacts']
    if topup is False:
        del sections['Diffusion']['Susceptibility distortion correction']

    output_html_file = os.path.join(output_dir_base,sub,ses+".html")
    with open(output_html_file,'w') as htmlFile:
        htmlFile.write(template.render(summary=summary,sections=sections))