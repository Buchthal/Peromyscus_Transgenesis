# Activity tracking with cameras

Most code in this folder was written by Christy Dennison and Boqiang Tu.

- `.`: runs on all Pis
- `visible_light`: regularly taking pictures with visible light cameras, and computing activity data with imagediff.
- `thermal`: like visible light cameras, but with thermal cameras (FLIR lepton).
- `ir_analysis`: server-side analysis of images with IR illumination (taken with visible light cameras)
- `thermal_analysis`: server-side analysis of images taken with thermal cameras

All code except `ir_analysis` and `thermal_analysis` runs locally on the Pis.
