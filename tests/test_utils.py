#!/usr/bin/env python3

import pytest
import logging

import dmri_preprocessing.utils as utils
import dmri_preprocessing.dmri_preprocessing as dmri_preprocessing

logger = logging.getLogger()

def mock_options():
    mock_opts = dmri_preprocessing.parse_args(
        [
            'tests/ds002080', 
            'tests/ds002080/derivatives',
            'participant',
            '--participant_label',
            'sub-CON02',
            '--session_label',
            'ses-postop',
            '--work_dir',
            'work'
        ]
    )
    return mock_opts

def test_get_bids_layout():
    opts = mock_options()

    bids_dir = opts.bids_dir
    subject = opts.participant_label.replace("sub-","")
    session = opts.session_label.replace("ses-","")

    layout, subject_data = utils.get_bids_layout(bids_dir,subject,session)
    assert bids_dir in layout.root
    assert subject_data['subject'] == subject
    assert subject_data['session'] == session
    assert len(subject_data['dwi']) == 2

def test_get_overview_of_data():
    opts = mock_options()

    bids_dir = opts.bids_dir
    subject = opts.participant_label.replace("sub-","")
    session = opts.session_label.replace("ses-","")

    layout, subject_data = utils.get_bids_layout(bids_dir,subject,session)

    b0_threshold = opts.b0_threshold
    data = utils.get_overview_of_data(subject_data, layout, b0_threshold)

    assert(data['dwi'][0]['filename']==subject_data['dwi'][0])
    assert(data['dwi'][1]['filename']==subject_data['dwi'][1])
    assert(len(data['fmap'])==0)
    assert(len(data['dwi'][0]['metadata'])>0)
    assert(len(data['dwi'][1]['metadata'])>0)
    assert(len(data['dwi'][0]['b0_idx'])>0)
    assert(len(data['dwi'][1]['b0_idx'])>0)
    assert(len(data['dwi'][0]['bhigh_idx'])>0)
    assert(len(data['dwi'][1]['bhigh_idx'])==0)

def test_check_opposite_directions():
    assert utils.check_opposite_directions(['y']) == False
    assert utils.check_opposite_directions(['y','y-']) == True
    assert utils.check_opposite_directions(['y','y','x']) == False
    assert utils.check_opposite_directions(['y','y','x','y-']) == True

def test_check_if_dataset_compatible_with_topup():
    # Check if topup options are correct for test dataset
    opts = mock_options()

    bids_dir = opts.bids_dir
    subject = opts.participant_label.replace("sub-","")
    session = opts.session_label.replace("ses-","")

    layout, subject_data = utils.get_bids_layout(bids_dir,subject,session)

    b0_threshold = opts.b0_threshold
    data = utils.get_overview_of_data(subject_data, layout, b0_threshold)

    topup_options, phase_encoding_directions = utils.check_if_dataset_compatible_with_topup(data)

    assert topup_options['do_topup'] == True, 'topup options do_topup wrong'
    assert topup_options['only_dwi'] == True, 'topup options only_dwi wrong'
    assert topup_options['only_fmap'] == False, 'topup options only_fmap wrong'
    assert topup_options['only_sbref'] == False, 'topup options only_sbref wrong'
    assert topup_options['dwi_fmap_combined'] == False, 'topup options dwi_fmap_combined wrong'
    assert phase_encoding_directions['dwi'] == ['y-','y']
    assert phase_encoding_directions['fmap'] == []
    assert phase_encoding_directions['sbref'] == []

    # test other combinations
    # mock 1
    data = {}
    data['dwi'] = [{
        'filename': 'mock1',
        'metadata': {
            'PhaseEncodingDirection': 'y'
        },
        'b0_idx': [0,1,2]
    }]
    data['fmap'] = []
    data['sbref'] = []
    topup_options, phase_encoding_directions = utils.check_if_dataset_compatible_with_topup(data)
    assert topup_options['do_topup'] == False, 'topup options do_topup wrong for mock1'
    assert topup_options['only_dwi'] == False, 'topup options only_dwi wrong for mock1'
    assert topup_options['only_fmap'] == False, 'topup options only_fmap wrong for mock1'
    assert topup_options['only_sbref'] == False, 'topup options only_sbref wrong for moc1'
    assert topup_options['dwi_fmap_combined'] == False, 'topup options dwi_fmap_combined wrong for mock1'
    assert phase_encoding_directions['dwi'] == ['y']
    assert phase_encoding_directions['fmap'] == []
    assert phase_encoding_directions['sbref'] == []

    # mock 2
    data = {}
    data['dwi'] = [{
        'filename': 'mock2_dwi',
        'metadata': {
            'PhaseEncodingDirection': 'y'
        },
        'b0_idx': [0,1,2]
    }]
    data['fmap'] = [{
        'filename': 'mock2_fmap',
        'metadata': {
            'PhaseEncodingDirection': 'y-'
        },
    }]
    data['sbref'] = []
    topup_options, phase_encoding_directions = utils.check_if_dataset_compatible_with_topup(data)
    assert topup_options['do_topup'] == True, 'topup options do_topup wrong for mock2'
    assert topup_options['only_dwi'] == False, 'topup options only_dwi wrong for mock2'
    assert topup_options['only_fmap'] == False, 'topup options only_fmap wrong for mock2'
    assert topup_options['only_sbref'] == False, 'topup options only_sbref wrong for mock2'
    assert topup_options['dwi_fmap_combined'] == True, 'topup options dwi_fmap_combined wrong for mock2'
    assert phase_encoding_directions['dwi'] == ['y']
    assert phase_encoding_directions['fmap'] == ['y-']
    assert phase_encoding_directions['sbref'] == []

    # mock 3
    data = {}
    data['dwi'] = [{
        'filename': 'mock3_dwi',
        'metadata': {
            'PhaseEncodingDirection': 'y'
        },
        'b0_idx': [0,1,2]
    }]
    data['fmap'] = [
        {
            'filename': 'mock3_fmap1',
            'metadata': {
                'PhaseEncodingDirection': 'y-'
            },
        },
        {
            'filename': 'mock3_fmap2',
            'metadata': {
                'PhaseEncodingDirection': 'y'
            },
        },
    ]
    data['sbref'] = []
    topup_options, phase_encoding_directions = utils.check_if_dataset_compatible_with_topup(data)
    assert topup_options['do_topup'] == True, 'topup options do_topup wrong for mock 3'
    assert topup_options['only_dwi'] == False, 'topup options only_dwi wrong for mock 3'
    assert topup_options['only_fmap'] == True, 'topup options only_fmap wrong for mock 3'
    assert topup_options['only_sbref'] == False, 'topup options only_sbref wrong for mock 3'
    assert topup_options['dwi_fmap_combined'] == True, 'topup options dwi_fmap_combined wrong for mock 3'
    assert phase_encoding_directions['dwi'] == ['y']
    assert phase_encoding_directions['fmap'] == ['y-','y']
    assert phase_encoding_directions['sbref'] == []

    # mock 4
    data = {}
    data['dwi'] = [{
        'filename': 'mock4_dwi',
        'metadata': {
            'PhaseEncodingDirection': 'y'
        },
        'b0_idx': [0,1,2]
    }]
    data['fmap'] = [
        {
            'filename': 'mock4_fmap1',
            'metadata': {
                'PhaseEncodingDirection': 'y-'
            },
        },
        {
            'filename': 'mock4_fmap2',
            'metadata': {
                'PhaseEncodingDirection': 'y'
            },
        },
    ]
    data['sbref'] = [
        {
            'filename': 'mock4_sbref1',
            'metadata': {
                'PhaseEncodingDirection': 'y-'
            },
        },
        {
            'filename': 'mock4_sbref2',
            'metadata': {
                'PhaseEncodingDirection': 'y'
            },
        },
    ]
    topup_options, phase_encoding_directions = utils.check_if_dataset_compatible_with_topup(data)
    assert topup_options['do_topup'] == True, 'topup options do_topup wrong for mock 4'
    assert topup_options['only_dwi'] == False, 'topup options only_dwi wrong for mock 4'
    assert topup_options['only_fmap'] == True, 'topup options only_fmap wrong for mock 4'
    assert topup_options['only_sbref'] == True, 'topup options only_sbref wrong for mock 4'
    assert topup_options['dwi_fmap_combined'] == True, 'topup options dwi_fmap_combined wrong for mock 4'
    assert phase_encoding_directions['dwi'] == ['y']
    assert phase_encoding_directions['fmap'] == ['y-','y']
    assert phase_encoding_directions['sbref'] == ['y-','y']

    # mock 5
    data = {}
    data['dwi'] = [
        {
            'filename': 'mock5_dwi1',
            'metadata': {
                'PhaseEncodingDirection': 'y'
            },
            'b0_idx': [0,1,2]
        },
        {
            'filename': 'mock5_dwi2',
            'metadata': {
                'PhaseEncodingDirection': 'y-'
            },
            'b0_idx': [0,1,2]
        }
        ]
    data['fmap'] = [
        {
            'filename': 'mock5_fmap1',
            'metadata': {
                'PhaseEncodingDirection': 'y-'
            },
        },
        {
            'filename': 'mock5_fmap2',
            'metadata': {
                'PhaseEncodingDirection': 'y'
            },
        },
    ]
    data['sbref'] = [
        {
            'filename': 'mock5_sbref1',
            'metadata': {
                'PhaseEncodingDirection': 'y-'
            },
        },
        {
            'filename': 'mock5_sbref2',
            'metadata': {
                'PhaseEncodingDirection': 'y'
            },
        },
    ]
    topup_options, phase_encoding_directions = utils.check_if_dataset_compatible_with_topup(data)
    assert topup_options['do_topup'] == True, 'topup options do_topup wrong for mock 5'
    assert topup_options['only_dwi'] == True, 'topup options only_dwi wrong for mock 5'
    assert topup_options['only_fmap'] == True, 'topup options only_fmap wrong for mock 5'
    assert topup_options['only_sbref'] == True, 'topup options only_sbref wrong for mock 5'
    assert topup_options['dwi_fmap_combined'] == True, 'topup options dwi_fmap_combined wrong for mock 5'
    assert phase_encoding_directions['dwi'] == ['y','y-']
    assert phase_encoding_directions['fmap'] == ['y-','y']
    assert phase_encoding_directions['sbref'] == ['y-','y']

def test_edit_phase_encoding_dir_metadata():
    dir_e = ['x','y','z','x-','y-','z-']
    i = 0
    for dir in ['i','j','k','i-','j-','k-']:
        metadata = {'PhaseEncodingDirection': dir}
        metadata_e = utils.edit_phase_encoding_dir_metadata(metadata)
        assert metadata_e['PhaseEncodingDirection'] == dir_e[i]
        i += 1
    