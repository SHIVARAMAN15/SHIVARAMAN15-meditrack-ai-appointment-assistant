import React from 'react';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  CartesianGrid
} from 'recharts';
import { BarChart2, PieChart as PieIcon, TrendingUp, Layers } from 'lucide-react';

const RISK_COLORS = ['#10b981', '#f59e0b', '#ef4444'];
const OUTCOME_COLORS = ['#10b981', '#ef4444', '#0284c7', '#94a3b8'];

export default function AnalyticsCharts({ trends, loading }) {
  if (loading || !trends) {
    return (
      <div className="state-container" style={{ minHeight: '300px' }}>
        <div className="spinner" />
        <span>Aggregating clinic attendance metrics and trend projections...</span>
      </div>
    );
  }

  const { outcomes = [], risk_distribution = [], daily_trends = [], department_breakdown = [] } = trends;

  // Format short date for XAxis
  const formattedDailyTrends = daily_trends.map((item) => ({
    ...item,
    formattedDate: item.date ? item.date.slice(5) : '',
  }));

  return (
    <div className="charts-grid">
      {/* 1. Daily Volume and Status Trends */}
      <div className="chart-card">
        <div className="chart-header">
          <div>
            <div className="chart-title">Appointment Flow &amp; Status (7-Day Window)</div>
            <div className="chart-desc">Historical and scheduled appointment activity by calendar day</div>
          </div>
          <TrendingUp size={18} style={{ color: 'var(--primary)' }} />
        </div>
        <div style={{ width: '100%', height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={formattedDailyTrends} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
              <XAxis dataKey="formattedDate" tick={{ fontSize: 11 }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: '11px', paddingTop: '6px' }} />
              <Bar dataKey="scheduled" name="Scheduled" fill="#0284c7" stackId="a" radius={[0, 0, 0, 0]} />
              <Bar dataKey="completed" name="Completed" fill="#10b981" stackId="a" radius={[0, 0, 0, 0]} />
              <Bar dataKey="no_show" name="No-Show" fill="#ef4444" stackId="a" radius={[0, 0, 0, 0]} />
              <Bar dataKey="cancelled" name="Cancelled" fill="#94a3b8" stackId="a" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 2. Upcoming Risk Category Distribution */}
      <div className="chart-card">
        <div className="chart-header">
          <div>
            <div className="chart-title">ML Risk Categorization (Upcoming Slots)</div>
            <div className="chart-desc">Attendance risk classification distribution for upcoming scheduled visits</div>
          </div>
          <PieIcon size={18} style={{ color: 'var(--warning)' }} />
        </div>
        <div style={{ width: '100%', height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={risk_distribution}
                dataKey="count"
                nameKey="category"
                cx="50%"
                cy="50%"
                outerRadius={85}
                innerRadius={50}
                paddingAngle={4}
                label={({ percent }) => `${(percent * 100).toFixed(0)}%`}
              >
                {risk_distribution.map((entry, index) => (
                  <Cell key={`risk-cell-${index}`} fill={entry.color || RISK_COLORS[index % RISK_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: '11px' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 3. Department Workload */}
      <div className="chart-card">
        <div className="chart-header">
          <div>
            <div className="chart-title">Department Workload Breakdown</div>
            <div className="chart-desc">Total patient appointment volume distributed across clinical departments</div>
          </div>
          <Layers size={18} style={{ color: 'var(--primary)' }} />
        </div>
        <div style={{ width: '100%', height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={department_breakdown}
              layout="vertical"
              margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#e2e8f0" />
              <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
              <YAxis dataKey="department" type="category" tick={{ fontSize: 11 }} width={90} />
              <Tooltip />
              <Bar dataKey="count" name="Appointments" fill="#0284c7" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 4. Historical Outcome Proportions */}
      <div className="chart-card">
        <div className="chart-header">
          <div>
            <div className="chart-title">Historical Appointment Outcomes</div>
            <div className="chart-desc">Clinic-wide distribution of resolved vs active appointment states</div>
          </div>
          <BarChart2 size={18} style={{ color: 'var(--success)' }} />
        </div>
        <div style={{ width: '100%', height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={outcomes}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={85}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
              >
                {outcomes.map((entry, index) => (
                  <Cell key={`outcome-cell-${index}`} fill={entry.color || OUTCOME_COLORS[index % OUTCOME_COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: '11px' }} />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
