import React, { useState } from 'react';
import { X, Calendar, Activity, RefreshCw, ShieldAlert } from 'lucide-react';

const ALLOWED_DEPARTMENTS = [
  'General Practice',
  'Cardiology',
  'Dermatology',
  'Orthopedics',
  'Pediatrics',
  'Neurology',
  'Oncology',
  'Endocrinology',
];

export function CreateAppointmentModal({ isOpen, onClose, onSubmit, submitting }) {
  const [patientName, setPatientName] = useState('');
  const [department, setDepartment] = useState('General Practice');
  const [dateTime, setDateTime] = useState('');
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');

  if (!isOpen) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (!patientName.trim()) {
      setError('Patient name is required.');
      return;
    }
    if (!dateTime) {
      setError('Appointment date and time is required.');
      return;
    }

    const selectedDate = new Date(dateTime);
    if (selectedDate <= new Date()) {
      setError('Appointment date and time must be set in the future.');
      return;
    }

    onSubmit({
      patient_name: patientName.trim(),
      department,
      appointment_datetime: selectedDate.toISOString(),
      notes: notes.trim(),
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <Calendar size={20} style={{ color: 'var(--primary)' }} />
            Schedule New Appointment
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div style={{ padding: '10px 14px', background: 'var(--danger-light)', color: 'var(--danger-dark)', borderRadius: 'var(--radius-md)', fontSize: '0.825rem' }}>
                {error}
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Patient Full Name *</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. John Doe"
                value={patientName}
                onChange={(e) => setPatientName(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">Clinical Department *</label>
              <select
                className="form-select"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
              >
                {ALLOWED_DEPARTMENTS.map((dept) => (
                  <option key={dept} value={dept}>
                    {dept}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Appointment Date &amp; Time (UTC Local) *</label>
              <input
                type="datetime-local"
                className="form-input"
                value={dateTime}
                onChange={(e) => setDateTime(e.target.value)}
                required
              />
              <span className="form-hint">Must be scheduled for a future date/time. Double-booking within 30 min is prevented.</span>
            </div>

            <div className="form-group">
              <label className="form-label">Clinical Notes / Reason</label>
              <textarea
                className="form-textarea"
                rows={3}
                placeholder="Optional clinical notes or visit reason..."
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Creating...' : 'Confirm Appointment'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function RescheduleModal({ isOpen, appointment, onClose, onSubmit, submitting }) {
  const [newDateTime, setNewDateTime] = useState('');
  const [error, setError] = useState('');

  if (!isOpen || !appointment) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');

    if (!newDateTime) {
      setError('Please select a new appointment date and time.');
      return;
    }

    const selected = new Date(newDateTime);
    if (selected <= new Date()) {
      setError('The rescheduled time must be set in the future.');
      return;
    }

    onSubmit(appointment.id, {
      appointment_datetime: selected.toISOString(),
      version: appointment.version,
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <RefreshCw size={20} style={{ color: 'var(--primary)' }} />
            Reschedule Appointment {appointment.appointment_code}
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div style={{ padding: '10px 14px', background: 'var(--danger-light)', color: 'var(--danger-dark)', borderRadius: 'var(--radius-md)', fontSize: '0.825rem' }}>
                {error}
              </div>
            )}

            <div className="details-grid">
              <div className="detail-item">
                <span className="detail-label">Patient</span>
                <span className="detail-value">{appointment.patient_name}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Department</span>
                <span className="detail-value">{appointment.department}</span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Currently Scheduled</span>
                <span className="detail-value" style={{ fontSize: '0.82rem' }}>
                  {new Date(appointment.appointment_datetime).toLocaleString()}
                </span>
              </div>
              <div className="detail-item">
                <span className="detail-label">Concurrency Version</span>
                <span className="detail-value mono">v{appointment.version}</span>
              </div>
            </div>

            <div className="form-group" style={{ marginTop: '8px' }}>
              <label className="form-label">New Appointment Date &amp; Time *</label>
              <input
                type="datetime-local"
                className="form-input"
                value={newDateTime}
                onChange={(e) => setNewDateTime(e.target.value)}
                required
              />
              <span className="form-hint">
                Optimistic locking will automatically protect against conflicting changes.
              </span>
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={submitting}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Rescheduling...' : 'Save Rescheduled Slot'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function CancelModal({ isOpen, appointment, onClose, onSubmit, submitting }) {
  const [reason, setReason] = useState('Patient requested cancellation');

  if (!isOpen || !appointment) return null;

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(appointment.id, {
      reason: reason.trim(),
      version: appointment.version,
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title" style={{ color: 'var(--danger)' }}>
            <ShieldAlert size={20} />
            Confirm Cancellation
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            <p style={{ fontSize: '0.875rem', color: 'var(--neutral-700)' }}>
              Are you sure you want to cancel appointment <strong>{appointment.appointment_code}</strong> for{' '}
              <strong>{appointment.patient_name}</strong>?
            </p>

            <div style={{ padding: '12px', background: 'var(--neutral-50)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', fontSize: '0.825rem' }}>
              <div><strong>Department:</strong> {appointment.department}</div>
              <div><strong>Scheduled for:</strong> {new Date(appointment.appointment_datetime).toLocaleString()}</div>
            </div>

            <div className="form-group">
              <label className="form-label">Cancellation Reason</label>
              <input
                type="text"
                className="form-input"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. Patient called to cancel, schedule conflict"
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={submitting}>
              Keep Appointment
            </button>
            <button type="submit" className="btn btn-danger" disabled={submitting}>
              {submitting ? 'Cancelling...' : 'Confirm Cancellation'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export function DetailPredictionModal({
  isOpen,
  appointment,
  onClose,
  onRefreshPrediction,
  refreshingPrediction,
}) {
  if (!isOpen || !appointment) return null;

  const pred = appointment.latest_prediction;
  const attendProb = pred ? Math.round(pred.attendance_probability * 100) : null;
  const noShowProb = pred ? Math.round(pred.no_show_probability * 100) : null;
  const riskCat = pred?.risk_category || 'low';
  const features = pred?.features || {};

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" style={{ maxWidth: '680px' }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">
            <Activity size={20} style={{ color: 'var(--primary)' }} />
            Appointment Details &amp; ML Prediction
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {/* Top metadata grid */}
          <div className="details-grid">
            <div className="detail-item">
              <span className="detail-label">Appointment Code</span>
              <span className="detail-value mono">{appointment.appointment_code}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Patient Name &amp; Ref</span>
              <span className="detail-value">
                {appointment.patient_name} ({appointment.patient_reference})
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Department</span>
              <span className="detail-value">{appointment.department}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Status</span>
              <div>
                <span className={`badge badge-status-${appointment.status}`}>
                  {appointment.status.replace('_', ' ')}
                </span>
              </div>
            </div>
            <div className="detail-item">
              <span className="detail-label">Scheduled Date &amp; Time</span>
              <span className="detail-value" style={{ fontSize: '0.85rem' }}>
                {new Date(appointment.appointment_datetime).toLocaleString()}
              </span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Concurrency Version</span>
              <span className="detail-value mono">v{appointment.version}</span>
            </div>
          </div>

          {appointment.notes && (
            <div style={{ padding: '10px 14px', background: 'var(--neutral-50)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-color)', fontSize: '0.85rem' }}>
              <strong>Notes:</strong> {appointment.notes}
            </div>
          )}

          {/* Machine Learning Prediction Card */}
          <div style={{ padding: '16px', background: 'white', borderRadius: 'var(--radius-lg)', border: '1px solid var(--border-color)', boxShadow: 'var(--shadow-sm)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
              <div style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--neutral-900)' }}>
                Machine Learning Attendance Assessment
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => onRefreshPrediction(appointment.id)}
                disabled={refreshingPrediction}
                title="Re-run prediction pipeline with latest parameters"
              >
                <RefreshCw size={13} className={refreshingPrediction ? 'spinner' : ''} />
                <span>{refreshingPrediction ? 'Recalculating...' : 'Recalculate'}</span>
              </button>
            </div>

            {pred ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {/* Visual Probability Gauge */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <span style={{ fontSize: '1.75rem', fontWeight: 700, color: riskCat === 'high' ? 'var(--danger)' : 'var(--neutral-900)' }}>
                      {attendProb}%
                    </span>
                    <span style={{ fontSize: '0.85rem', color: 'var(--neutral-500)', marginLeft: '6px' }}>
                      Likelihood to Attend
                    </span>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <span className={`badge badge-risk-${riskCat}`} style={{ fontSize: '0.85rem', padding: '4px 12px' }}>
                      {riskCat.toUpperCase()} NO-SHOW RISK ({noShowProb}%)
                    </span>
                  </div>
                </div>

                <div className="prob-bar-bg" style={{ height: '10px' }}>
                  <div
                    className={`prob-bar-fill prob-bar-${riskCat}`}
                    style={{ width: `${attendProb}%` }}
                  />
                </div>

                {/* Model features breakdown */}
                <div style={{ marginTop: '8px' }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, textTransform: 'uppercase', color: 'var(--neutral-500)', marginBottom: '8px' }}>
                    Identified Predictor Factors
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '8px' }}>
                    <div className="detail-item" style={{ padding: '8px' }}>
                      <span className="detail-label">Lead Time</span>
                      <span className="detail-value">{features.lead_time_days ?? '--'} days</span>
                    </div>
                    <div className="detail-item" style={{ padding: '8px' }}>
                      <span className="detail-label">Appt Hour</span>
                      <span className="detail-value">{features.appointment_hour ? `${features.appointment_hour}:00` : '--'}</span>
                    </div>
                    <div className="detail-item" style={{ padding: '8px' }}>
                      <span className="detail-label">Prior Visits</span>
                      <span className="detail-value">{features.previous_appointments ?? 0}</span>
                    </div>
                    <div className="detail-item" style={{ padding: '8px' }}>
                      <span className="detail-label">Prior No-Shows</span>
                      <span className="detail-value" style={{ color: (features.previous_no_shows ?? 0) > 0 ? 'var(--danger)' : 'inherit' }}>
                        {features.previous_no_shows ?? 0}
                      </span>
                    </div>
                    <div className="detail-item" style={{ padding: '8px' }}>
                      <span className="detail-label">Reminder Dispatched</span>
                      <span className="detail-value">{features.had_previous_reminder ? 'Yes' : 'No'}</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ textAlign: 'center', padding: '16px', color: 'var(--neutral-500)', fontSize: '0.85rem' }}>
                No prediction recorded yet. Click &quot;Recalculate&quot; to score this appointment.
              </div>
            )}
          </div>

          {/* Reminder History */}
          {appointment.reminders && appointment.reminders.length > 0 && (
            <div>
              <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--neutral-800)', marginBottom: '8px' }}>
                Simulated Reminder Logs ({appointment.reminders.length})
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {appointment.reminders.map((rem) => (
                  <div
                    key={rem.id}
                    style={{
                      padding: '8px 12px',
                      background: 'var(--neutral-50)',
                      borderRadius: 'var(--radius-sm)',
                      border: '1px solid var(--border-color)',
                      fontSize: '0.78rem',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                    }}
                  >
                    <span>
                      <strong>{rem.reminder_channel.replace('_', ' ').toUpperCase()}</strong>: {rem.simulated_message}
                    </span>
                    <span className="badge badge-status-completed" style={{ fontSize: '0.7rem' }}>
                      Sent
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
