# python_dmri_preprocessing

## Installation
Install using docker:
```
docker build -t dmri_preprocessing .
```
## Usage
Only works on one subject and session at the time. You can't process multiple sessions and/or subjects.
```
usage: docker run dmri_preprocessing [-h] [-v] [--participant_label PARTICIPANT_LABEL]
                             [--session_label SESSION_LABEL] [--n_cpus N_CPUS]
                             [--b0-threshold B0_THRESHOLD]
                             [--dwi_denoise_window DWI_DENOISE_WINDOW]
                             [-w WORK_DIR]
                             bids_dir output_dir {participant}

dmri_preprocessing: dMRI preprocessing.

positional arguments:
  bids_dir              the root folder of a BIDS valid dataset (sub-XXXXX
                        folders should be found at the top level in this
                        folder).
  output_dir            the output path for the outcomes of preprocessing and
                        visual reports
  {participant}         processing stage to be run, only "participant" in the
                        case of dmri_preprocessing (see BIDS-Apps
                        specification).

optional arguments:
  -h, --help            show this help message and exit
  -v, --version         show program's version number and exit

Options for filtering BIDS queries:
  --participant_label PARTICIPANT_LABEL, --participant-label PARTICIPANT_LABEL
                        a single subject identifier (the sub- prefix can be
                        removed) (default: None)
  --session_label SESSION_LABEL, --session-label SESSION_LABEL
                        a single session identifier (the ses- prefix can be
                        removed) (default: None)

Options to handle performance:
  --n_cpus N_CPUS, --n-cpus N_CPUS, --nthreads N_CPUS
                        maximum number of threads across all processes
                        (default: 1)

Workflow configuration:
  --b0-threshold B0_THRESHOLD, --b0_threshold B0_THRESHOLD
                        any value in the .bval file less than this will be
                        considered a b=0 image. Current default threshold =
                        100; this threshold can be lowered or increased. Note,
                        setting this too high can result in inaccurate
                        results. (default: 100)
  --dwi_denoise_window DWI_DENOISE_WINDOW, --dwi-denoise-window DWI_DENOISE_WINDOW
                        window size in voxels for ``dwidenoise``. Must be odd.
                        (default: 5)

Other options:
  -w WORK_DIR, --work-dir WORK_DIR, --work_dir WORK_DIR
                        path where intermediate results should be stored
                        (default: None)
```

## Example
```
docker run dmri_preprocessing data_in data_out participant \
    --participant_label 01 \
    --session_label 01 \
    -w work_dir \
    --n_cpus 2
```

## Preprocessing steps

`dmri_preprocessing` is based on nipype v. 1.4.2. It runs the following processing steps:
- Data info extraction and merging
- Noise estimation and denoising using Marchenko-Pastur PCA (mrtrix3 `dwidenoise`)
- Removal of Gibbs ringing artifacts (mrtrix3 `mrdegibbs`)
- Estimation of susceptibility induced distortions (fsl `topup`)
- eddy current and movement correction (fsl `eddy`)
- Bias field correction (ants `N4BiasfieldCorrection`)
- Fit diffusion tensor modelling with fsl `dtifit`
- Calculate radial diffusivity using output from fsl `dtifit` 

### Data info extraction and merging
If we have multiple dwi sequences, the sequences with same phase encoding directions are merged. 

Note: Now, the pipeline only works with the dwi sequences having the same phase encoding direction. If we would have two dwi sequences with opposite directions, the pipeline would only process one of them (ref. #26)

###  Noise estimation and denoising using Marchenko-Pastur PCA
The pipeline uses `mrtrix3` `dwidenoise` to do Marchenko-Pastur PCA (MP-PCA). The size of the denoising window can be set with the `--dwi_denoise_window` flag. Default is 5.

### Removal of Gibbs ringing artifacts
The removal of Gibbs ringing artifacts are done on data acquired in full k-space with `mrtrix3` `mrdegibbs`. It checks the field `PartialFourier` in the `.json` file.

### Estimation of susceptibility distortion correction
The susceptibility distortion correction (sdc) is done by `fsl` `topup`. The phase encoding maps used for the estimations are chosen with the following order:
1. single band references (sbref) in both phase encoding directions
2. stand alone fieldmaps acquired in both phase encoding directions
3. b0 frames from dwi merged with phase encoding maps in the opposite direction.
If we do not have opposite phase encocing direction maps, the estimation of sdc is not run. 

### Eddy current and movement correction
`fsl` `eddy` is used for eddy current and movement correction. This step also applies the sdc if `topup` was done. `eddy` runs with standard parameters, except that the `--repol` and `--cnr_maps` flags are set to `True`.

 ### Bias field correction
This step estimates the bias field correction on the first b0 image, then we apply this correction on all the frames inside the dwi using `fslmaths`.

### Diffusion tensor modelling
Diffusion tensor modelling is done by `fsl` `dtifit` which fits a tensor model at each voxel.

### Radial diffusitiivity
The radial diffusitivity was calculated by using fslmaths to average eigenvalue maps 2 and 3: (l2 + l3)/2

## Other
Code is inspired by [qsiprep](https://github.com/PennBBL/qsiprep).
