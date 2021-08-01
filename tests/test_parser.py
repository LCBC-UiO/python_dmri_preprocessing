#!/usr/bin/env python3

import logging
import pytest

from dmri_preprocessing import dmri_preprocessing

logger = logging.getLogger(__name__)

def test_parser():
    """
    Test parser functions
    """
    # Check positional arguments
    opts = dmri_preprocessing.parse_args(['bids_dir', 'output_dir','participant','--participant_label','sub-1234','--session_label','ses-02','--work_dir','work_dir'])
    assert opts.bids_dir != "", "empty positional argument, contains error elements"
    assert opts.output_dir != "", "empty positional argument, contains error elements"
    assert opts.analysis_level != "", "empty positional argument, contains error elements"
    
    # Check if positional arguments are not set, or partially set
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        dmri_preprocessing.parse_args([])
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 2
    
    with pytest.raises(SystemExit) as pytest_wrapped_e:
        dmri_preprocessing.parse_args(['bids_dir','output_dir','participant'])
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 2

    with pytest.raises(SystemExit) as pytest_wrapped_e:
        dmri_preprocessing.parse_args(['bids_dir','output_dir','participant','--participant_label','2'])
    assert pytest_wrapped_e.type == SystemExit
    assert pytest_wrapped_e.value.code == 2

