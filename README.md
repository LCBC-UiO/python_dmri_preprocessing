# python_dmri_preprocessing
## Installation
This repository only contains python scripts to run the preprocessing of dMRI data. Only installation of the required python packages are necessary:
```
pip install -r requirements.txt
```
## Usage
Only works on one subject and session at the time. You can't process multiple sessions and/or subjects.
```
usage: dmri_preprocessing.py [-h] [-v] [--participant_label PARTICIPANT_LABEL]
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
                        If 0, ``dwidwenoise`` will not be run (default: 5)

Other options:
  -w WORK_DIR, --work-dir WORK_DIR, --work_dir WORK_DIR
                        path where intermediate results should be stored
                        (default: None)
```

## Example
```
python dmri_preprocessing.py data_in data_out participant \
    --participant_label 01 \
    --session_label 01 \
    -w work_dir \
    --n_cpus 2
```

## Other
Code is inspired by [qsiprep](https://github.com/PennBBL/qsiprep).
