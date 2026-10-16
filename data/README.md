# MediTrack AI Synthetic Data Directory

This directory stores generated synthetic data used for training and testing the MediTrack AI Attendance Prediction model.

## Synthetic Data Notice
All patient records, names, contact references, and appointment histories generated in this directory are 100% fictional and synthesized algorithmically. They do **not** reflect real patients, healthcare providers, or clinical records.

## Files
- `synthetic_appointments.csv`: Generated training dataset containing at least 1,200 synthetic appointment records with realistic lead times, historical attendance patterns, departments, and simulated outcome labels. (Excluded from git tracking as it can be regenerated reproducibly via `python backend/app/ml/generate_data.py`).
