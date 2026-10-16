import React from 'react';
import { Search, Calendar, Clock, ChevronLeft, ChevronRight, Eye, RefreshCw, XCircle, Send } from 'lucide-react';

const DEPARTMENTS = [
  'All Departments',
  'General Practice',
  'Cardiology',
  'Dermatology',
  'Orthopedics',
  'Pediatrics',
  'Neurology',
  'Oncology',
  'Endocrinology',
];

const STATUSES = [
  { label: 'All Statuses', value: '' },
  { label: 'Scheduled', value: 'scheduled' },
  { label: 'Completed', value: 'completed' },
  { label: 'Cancelled', value: 'cancelled' },
  { label: 'No-Show', value: 'no_show' },
];

const RISKS = [
  { label: 'All Risk Levels', value: '' },
  { label: 'Low Risk (<30%)', value: 'low' },
  { label: 'Medium Risk (30-60%)', value: 'medium' },
  { label: 'High Risk (≥60%)', value: 'high' },
];

export default function AppointmentTable({
  appointments,
  total,
  page,
  pages,
  _perPage,
  filters,
  onFilterChange,
  onPageChange,
  loading,
  onOpenDetailModal,
  onOpenRescheduleModal,
  onOpenCancelModal,
  onSendReminder,
}) {
  const formatDateTime = (isoString) => {
    if (!isoString) return '--';
    try {
      const dt = new Date(isoString);
      return dt.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <div className="panel-title">
            <Calendar size={18} style={{ color: 'var(--primary)' }} />
            Clinic Appointments
          </div>
          <div className="panel-subtitle">
            Showing {appointments.length} of {total} patient appointments
          </div>
        </div>
      </div>

      {/* Filter and Search Controls */}
      <div className="filters-bar">
        <div className="filter-group">
          <div className="search-input-wrapper">
            <Search size={16} />
            <input
              type="text"
              className="search-input"
              placeholder="Search by patient name, code, or PAT-..."
              value={filters.search}
              onChange={(e) => onFilterChange('search', e.target.value)}
            />
          </div>

          <select
            className="select-filter"
            value={filters.department}
            onChange={(e) => onFilterChange('department', e.target.value)}
          >
            {DEPARTMENTS.map((dept) => (
              <option key={dept} value={dept === 'All Departments' ? '' : dept}>
                {dept}
              </option>
            ))}
          </select>

          <select
            className="select-filter"
            value={filters.status}
            onChange={(e) => onFilterChange('status', e.target.value)}
          >
            {STATUSES.map((st) => (
              <option key={st.label} value={st.value}>
                {st.label}
              </option>
            ))}
          </select>

          <select
            className="select-filter"
            value={filters.risk_category}
            onChange={(e) => onFilterChange('risk_category', e.target.value)}
          >
            {RISKS.map((r) => (
              <option key={r.label} value={r.value}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Table Content */}
      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th>Ref Code</th>
              <th>Patient</th>
              <th>Department</th>
              <th>Date &amp; Time</th>
              <th>Status</th>
              <th>Predicted Attendance</th>
              <th style={{ textAlign: 'right' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7}>
                  <div className="state-container">
                    <div className="spinner" />
                    <span>Loading appointments and risk scores...</span>
                  </div>
                </td>
              </tr>
            ) : appointments.length === 0 ? (
              <tr>
                <td colSpan={7}>
                  <div className="state-container">
                    <Calendar size={36} style={{ color: 'var(--neutral-400)' }} />
                    <p style={{ fontWeight: 600, color: 'var(--neutral-700)' }}>
                      No matching appointments found
                    </p>
                    <p style={{ fontSize: '0.8rem' }}>
                      Try adjusting your search criteria or clear active filters.
                    </p>
                  </div>
                </td>
              </tr>
            ) : (
              appointments.map((apt) => {
                const pred = apt.latest_prediction;
                const attendProb = pred ? Math.round(pred.attendance_probability * 100) : null;
                const riskCat = pred?.risk_category || 'low';
                const isScheduled = apt.status === 'scheduled';

                return (
                  <tr key={apt.id}>
                    <td>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm mono"
                        onClick={() => onOpenDetailModal(apt)}
                        title="View details & ML predictions"
                        style={{ padding: '3px 8px', fontSize: '0.78rem' }}
                      >
                        {apt.appointment_code}
                      </button>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--neutral-900)' }}>
                        {apt.patient_name}
                      </div>
                      <div className="mono" style={{ fontSize: '0.75rem', color: 'var(--neutral-400)' }}>
                        {apt.patient_reference}
                      </div>
                    </td>
                    <td>
                      <span style={{ fontWeight: 500 }}>{apt.department}</span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Clock size={14} style={{ color: 'var(--neutral-400)' }} />
                        <span>{formatDateTime(apt.appointment_datetime)}</span>
                      </div>
                    </td>
                    <td>
                      <span className={`badge badge-status-${apt.status}`}>
                        {apt.status.replace('_', ' ')}
                      </span>
                    </td>
                    <td>
                      {pred ? (
                        <div className="prob-cell">
                          <div className="prob-labels">
                            <span style={{ color: riskCat === 'high' ? 'var(--danger-dark)' : 'var(--neutral-700)' }}>
                              {attendProb}% Attend
                            </span>
                            <span className={`badge badge-risk-${riskCat}`} style={{ padding: '1px 6px', fontSize: '0.68rem' }}>
                              {riskCat} risk
                            </span>
                          </div>
                          <div className="prob-bar-bg">
                            <div
                              className={`prob-bar-fill prob-bar-${riskCat}`}
                              style={{ width: `${attendProb}%` }}
                            />
                          </div>
                        </div>
                      ) : (
                        <span style={{ fontSize: '0.75rem', color: 'var(--neutral-400)' }}>
                          Pending scoring
                        </span>
                      )}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm btn-icon-only"
                          onClick={() => onOpenDetailModal(apt)}
                          title="View ML Prediction & Details"
                        >
                          <Eye size={14} />
                        </button>

                        {isScheduled && (
                          <>
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={() => onOpenRescheduleModal(apt)}
                              title="Reschedule appointment slot"
                            >
                              <RefreshCw size={13} />
                              <span>Reschedule</span>
                            </button>

                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={() => onSendReminder(apt.id)}
                              title="Simulate SMS Reminder"
                            >
                              <Send size={13} />
                            </button>

                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              style={{ color: 'var(--danger)' }}
                              onClick={() => onOpenCancelModal(apt)}
                              title="Cancel appointment"
                            >
                              <XCircle size={14} />
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      <div className="pagination-bar">
        <div>
          Showing page <strong>{page}</strong> of <strong>{pages || 1}</strong> &bull; Total {total} appointments
        </div>
        <div className="pagination-controls">
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={page <= 1 || loading}
            onClick={() => onPageChange(page - 1)}
          >
            <ChevronLeft size={14} />
            Previous
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            disabled={page >= pages || loading}
            onClick={() => onPageChange(page + 1)}
          >
            Next
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
