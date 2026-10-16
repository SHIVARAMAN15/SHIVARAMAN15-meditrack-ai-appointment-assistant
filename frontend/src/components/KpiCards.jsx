import React from 'react';
import { Calendar, CheckCircle2, AlertOctagon, Send, TrendingUp } from 'lucide-react';

export default function KpiCards({ summary, loading }) {
  if (loading || !summary) {
    return (
      <div className="kpi-grid">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="kpi-card">
            <div className="kpi-content" style={{ width: '100%' }}>
              <div className="kpi-title">Loading metric...</div>
              <div className="kpi-value" style={{ opacity: 0.5 }}>--</div>
              <div className="kpi-subtitle">Fetching operational data...</div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  // Calculate predicted attendance rate based on resolved appointments or ML baseline
  const attendanceRate = summary.historical_no_show_rate !== undefined
    ? Math.max(0, (100 - Number(summary.historical_no_show_rate))).toFixed(1)
    : '82.5';

  return (
    <div className="kpi-grid">
      {/* 1. Total Appointments */}
      <div className="kpi-card">
        <div className="kpi-content">
          <span className="kpi-title">Total Appointments</span>
          <span className="kpi-value">{summary.total_appointments ?? 0}</span>
          <span className="kpi-subtitle">
            <strong>{summary.scheduled_appointments ?? 0}</strong> active scheduled &bull; {summary.upcoming_appointments ?? 0} upcoming
          </span>
        </div>
        <div className="kpi-icon-wrapper kpi-blue">
          <Calendar size={22} />
        </div>
      </div>

      {/* 2. Predicted Attendance Rate */}
      <div className="kpi-card">
        <div className="kpi-content">
          <span className="kpi-title">Expected Attendance Rate</span>
          <span className="kpi-value">{attendanceRate}%</span>
          <span className="kpi-subtitle">
            <TrendingUp size={14} style={{ color: 'var(--success)' }} />
            Historical no-show rate: {summary.historical_no_show_rate ?? 0}%
          </span>
        </div>
        <div className="kpi-icon-wrapper kpi-green">
          <CheckCircle2 size={22} />
        </div>
      </div>

      {/* 3. High-Risk Appointments */}
      <div className="kpi-card">
        <div className="kpi-content">
          <span className="kpi-title">High-Risk No-Shows</span>
          <span className="kpi-value" style={{ color: (summary.high_risk_appointments ?? 0) > 0 ? 'var(--danger)' : 'inherit' }}>
            {summary.high_risk_appointments ?? 0}
          </span>
          <span className="kpi-subtitle">
            Upcoming visits with &ge;60% predicted no-show risk
          </span>
        </div>
        <div className="kpi-icon-wrapper kpi-red">
          <AlertOctagon size={22} />
        </div>
      </div>

      {/* 4. Simulated Reminders Sent */}
      <div className="kpi-card">
        <div className="kpi-content">
          <span className="kpi-title">Reminders Dispatched</span>
          <span className="kpi-value">{summary.total_reminders_sent ?? 0}</span>
          <span className="kpi-subtitle">
            Simulated notifications &bull; Duplicate protection on
          </span>
        </div>
        <div className="kpi-icon-wrapper kpi-purple">
          <Send size={22} />
        </div>
      </div>
    </div>
  );
}
