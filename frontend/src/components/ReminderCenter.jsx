import React, { useState } from 'react';
import { Bell, Send, CheckCircle2, Clock, RefreshCw } from 'lucide-react';

export default function ReminderCenter({
  recommendations,
  loading,
  includeMediumRisk,
  onToggleMediumRisk,
  onSendReminder,
  onRefresh,
  sendingId,
}) {
  const [filterDept, setFilterDept] = useState('All');

  const filtered = recommendations.filter((item) => {
    if (filterDept !== 'All' && item.department !== filterDept) return false;
    return true;
  });

  const departments = ['All', ...new Set(recommendations.map((r) => r.department))];

  return (
    <div className="panel">
      <div className="panel-header">
        <div>
          <div className="panel-title">
            <Bell size={18} style={{ color: 'var(--primary)' }} />
            AI Reminder Recommendations Center
          </div>
          <div className="panel-subtitle">
            Automated recommendations based on predicted no-show risk with duplicate dispatch prevention
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onRefresh}
            disabled={loading}
          >
            <RefreshCw size={14} className={loading ? 'spinner' : ''} />
            <span>Refresh Recommendations</span>
          </button>
        </div>
      </div>

      {/* Control bar */}
      <div className="filters-bar">
        <div className="filter-group">
          <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', cursor: 'pointer', fontWeight: 500 }}>
            <input
              type="checkbox"
              checked={includeMediumRisk}
              onChange={(e) => onToggleMediumRisk(e.target.checked)}
              style={{ cursor: 'pointer', accentColor: 'var(--primary)' }}
            />
            Include Medium Risk (Upcoming within 7 days)
          </label>

          <div style={{ marginLeft: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--neutral-500)' }}>Department:</span>
            <select
              className="select-filter"
              value={filterDept}
              onChange={(e) => setFilterDept(e.target.value)}
              style={{ padding: '4px 10px', fontSize: '0.8rem' }}
            >
              {departments.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ fontSize: '0.8rem', color: 'var(--neutral-500)' }}>
          {filtered.length} patients require follow-up
        </div>
      </div>

      {/* Recommendations List */}
      <div className="panel-body" style={{ padding: '16px' }}>
        {loading ? (
          <div className="state-container">
            <div className="spinner" />
            <span>Analyzing risk thresholds and past dispatch records...</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="state-container">
            <CheckCircle2 size={40} style={{ color: 'var(--success)' }} />
            <p style={{ fontWeight: 600, color: 'var(--neutral-800)' }}>
              All high-risk appointments are up to date!
            </p>
            <p style={{ fontSize: '0.825rem' }}>
              No appointments currently exceed no-show risk thresholds or require immediate reminder dispatch.
            </p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {filtered.map((item) => {
              const isSending = sendingId === item.appointment_id;
              const noShowProb = Math.round(item.no_show_probability * 100);

              return (
                <div
                  key={item.appointment_id}
                  style={{
                    padding: '16px',
                    background: 'var(--neutral-50)',
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-md)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '10px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--neutral-900)' }}>
                          {item.patient_name}
                        </span>
                        <span className="mono" style={{ fontSize: '0.78rem', color: 'var(--neutral-500)' }}>
                          {item.appointment_code}
                        </span>
                        <span className={`badge badge-risk-${item.risk_category}`}>
                          {item.risk_category} risk ({noShowProb}%)
                        </span>
                        <span className="badge" style={{ background: 'var(--neutral-200)', color: 'var(--neutral-700)' }}>
                          {item.department}
                        </span>
                      </div>
                      <div style={{ fontSize: '0.8rem', color: 'var(--neutral-500)', marginTop: '4px' }}>
                        <Clock size={13} style={{ display: 'inline', marginRight: '4px', verticalAlign: '-1px' }} />
                        Scheduled for: {new Date(item.appointment_datetime).toLocaleString()} &bull; Reason: <strong>{item.reason}</strong>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      {item.already_reminded_recently && (
                        <span className="badge badge-risk-medium" title="A reminder was already sent in the last 24 hours">
                          Recent Reminder Sent
                        </span>
                      )}

                      <button
                        type="button"
                        className="btn btn-primary btn-sm"
                        disabled={!item.can_send || isSending}
                        onClick={() => onSendReminder(item.appointment_id)}
                      >
                        <Send size={13} className={isSending ? 'spinner' : ''} />
                        <span>
                          {isSending
                            ? 'Dispatching...'
                            : item.can_send
                            ? 'Dispatch Simulated SMS'
                            : 'Protected (Cooldown)'}
                        </span>
                      </button>
                    </div>
                  </div>

                  {/* Message Preview Box */}
                  <div
                    style={{
                      padding: '10px 14px',
                      background: 'white',
                      border: '1px solid var(--border-color)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.8rem',
                      color: 'var(--neutral-700)',
                      fontStyle: 'italic',
                    }}
                  >
                    &ldquo;{item.preview_message}&rdquo;
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
