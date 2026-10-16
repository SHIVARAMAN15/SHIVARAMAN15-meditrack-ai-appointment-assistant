"""
Generate synthetic historical appointment dataset for training the MediTrack attendance prediction model.

Notice: This dataset is 100% synthetic for demonstration and assessment purposes.
It does NOT contain real patient records or clinical outcomes.
"""
import os
from pathlib import Path
import numpy as np
import pandas as pd

ALLOWED_DEPARTMENTS = [
    "General Practice",
    "Cardiology",
    "Dermatology",
    "Orthopedics",
    "Pediatrics",
    "Neurology",
    "Oncology",
    "Endocrinology"
]

def generate_synthetic_data(num_samples: int = 1500, random_seed: int = 42) -> pd.DataFrame:
    """Generate synthetic historical appointment records with realistic behavioral correlations."""
    np.random.seed(random_seed)

    # 1. Lead time between booking and appointment (days)
    # Range 0 to 45 days, skewed towards 3-14 days
    lead_time_days = np.random.exponential(scale=10.0, size=num_samples).astype(int)
    lead_time_days = np.clip(lead_time_days, 0, 60)

    # 2. Appointment day of week (0=Mon, 4=Fri, 5=Sat)
    # Appointments are mostly Mon-Fri, few on Saturday
    days = np.random.choice([0, 1, 2, 3, 4, 5], size=num_samples, p=[0.22, 0.22, 0.20, 0.20, 0.12, 0.04])

    # 3. Appointment hour (8 to 17)
    hours = np.random.choice(range(8, 18), size=num_samples)

    # 4. Previous history
    # Previous appointments
    prev_appointments = np.random.poisson(lam=3.0, size=num_samples)
    prev_appointments = np.clip(prev_appointments, 0, 20)

    # Previous no-shows (cannot exceed previous appointments)
    prev_no_shows = []
    for prev in prev_appointments:
        if prev == 0:
            prev_no_shows.append(0)
        else:
            # Patients with more visits may have 0-3 no-shows
            ns = np.random.binomial(n=min(prev, 6), p=0.18)
            prev_no_shows.append(ns)
    prev_no_shows = np.array(prev_no_shows)

    # 5. Reminder sent (0 or 1)
    had_reminder = np.random.choice([0, 1], size=num_samples, p=[0.35, 0.65])

    # 6. Clinic Department
    departments = np.random.choice(ALLOWED_DEPARTMENTS, size=num_samples)

    # 7. Generate target label: attended (1) vs no-show (0)
    # Log-odds calculation based on documented healthcare factors:
    # Base log-odds of attending is positive (~75-80% attendance base rate)
    log_odds = 1.6

    # Factor: lead time (longer lead time increases no-show probability, i.e., reduces attendance)
    log_odds -= 0.035 * lead_time_days

    # Factor: previous no-show history (strong negative impact on attendance)
    log_odds -= 0.75 * prev_no_shows

    # Factor: established patient history (positive impact on attendance)
    log_odds += 0.12 * prev_appointments

    # Factor: reminder received (positive impact on attendance)
    log_odds += 0.55 * had_reminder

    # Factor: very early morning or late afternoon slightly lower attendance
    log_odds -= 0.25 * ((hours <= 8) | (hours >= 16)).astype(int)

    # Factor: Saturday appointments slightly lower attendance
    log_odds -= 0.30 * (days == 5).astype(int)

    # Department-specific adjustments (e.g., Oncology has higher commitment than Dermatology)
    dept_effects = {
        "Oncology": 0.5,
        "Cardiology": 0.3,
        "Neurology": 0.2,
        "General Practice": 0.0,
        "Orthopedics": -0.1,
        "Pediatrics": 0.1,
        "Endocrinology": 0.1,
        "Dermatology": -0.2
    }
    for dept, effect in dept_effects.items():
        log_odds += effect * (departments == dept).astype(int)

    # Add Gaussian noise for realistic unpredictability
    noise = np.random.normal(loc=0.0, scale=0.4, size=num_samples)
    log_odds += noise

    # Sigmoid function to derive attendance probability
    prob_attend = 1.0 / (1.0 + np.exp(-log_odds))

    # Binary outcome sampled from probability
    attended = (np.random.rand(num_samples) < prob_attend).astype(int)

    df = pd.DataFrame({
        "lead_time_days": lead_time_days,
        "day_of_week": days,
        "appointment_hour": hours,
        "previous_appointments": prev_appointments,
        "previous_no_shows": prev_no_shows,
        "had_previous_reminder": had_reminder,
        "department": departments,
        "attended": attended
    })

    return df

if __name__ == "__main__":
    current_dir = Path(__file__).resolve().parent
    workspace_root = current_dir.parent.parent.parent
    data_dir = workspace_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    out_file = data_dir / "synthetic_appointments.csv"

    print(f"Generating synthetic dataset with 1,500 records...")
    df = generate_synthetic_data(num_samples=1500, random_seed=42)
    df.to_csv(out_file, index=False)
    print(f"Saved dataset to {out_file}")
    print(f"Total rows: {len(df)}")
    print(f"Attendance distribution: Attended={sum(df['attended'] == 1)} ({sum(df['attended'] == 1)/len(df):.1%}), No-show={sum(df['attended'] == 0)} ({sum(df['attended'] == 0)/len(df):.1%})")
