0.3.0 (August 06, 2021)
=======================

  * [ENH] Add eddy output to derivatives and run eddy_quad (#35)
  * ENH: Initial tests on parser and utils (#33)
  * FIX: dmri_preprocessing import statements (#32)
  * [ENH] Test package build with github actions (#31)
  * [MAINT] Update documentation of pipeline (#29)
  * [MAINT] Remove misleading documentation (#28)

0.2.1 (January 28, 2021)
========================

  * [FIX] IndexError: tuple index out of range if the fmap does not contain multiple frames (#25)

0.2.0 (January 20, 2021)
========================

  * [ENH] Add Dockerfile for installing pipeline (#21)

0.1.0 (October 02, 2020)
========================

  * [ENH] Add radial diffusivity (RD) to the outputs (#15)
  * [FIX] Correct negligible difference between fmap and dwi voxel size. (#19)


0.0.5 (April 24, 2020)
======================

  * [FIX] Add as many entries to the enc_file.txt as it is frames in the fieldmaps. (#13)
  * [FIX] Error when creating dataset_description.json (#11)


0.0.4 (April 03, 2020)
======================

  * [FIX] Fix bug related to versioneer (leftover code) and matplotlib (#9)


0.0.3 (April 03, 2020)
======================

  * [MAINT] Use static versioning instead of versioneer. (#8)


0.0.2 (April 03, 2020)
======================

  * [FIX] Fixes bug with nipype and removes unecessary code. (#6)
  * MAINT: Update CHANGES.md automatically. (#4)
  * MAINT: Get version number automatic using versioneer. (#3)


0.0.1 (April 03, 2020)
======================

* Initial version with working preprocessing code.
