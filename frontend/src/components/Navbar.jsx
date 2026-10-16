import React from 'react';
import { Activity, Calendar, Bell, BarChart2, Plus, RefreshCw } from 'lucide-react';

export default function Navbar({
  activeTab,
  setActiveTab,
  health,
  onRefresh,
  onOpenCreateModal,
  isRefreshing
}) {
  const isHealthy = health && health.status === 'healthy';

  return (
    <header className="navbar">
      <div className="navbar-inner">
        <div className="brand-section">
          <div className="brand-logo">
            <Activity size={22} />
          </div>
          <div>
            <div className="brand-title">
              MediTrack AI
              <span className="brand-badge">Clinical v1.0</span>
            </div>
            <div className="brand-subtitle">
              Appointment Management &amp; Attendance Intelligence
            </div>
          </div>
        </div>

        {/* View Switcher Tabs */}
        <nav className="view-tabs" aria-label="Dashboard Views">
          <button
            type="button"
            className={`tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <Activity size={16} />
            Overview
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'appointments' ? 'active' : ''}`}
            onClick={() => setActiveTab('appointments')}
          >
            <Calendar size={16} />
            Appointments
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'reminders' ? 'active' : ''}`}
            onClick={() => setActiveTab('reminders')}
          >
            <Bell size={16} />
            Reminder Center
          </button>
          <button
            type="button"
            className={`tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
            onClick={() => setActiveTab('analytics')}
          >
            <BarChart2 size={16} />
            Analytics
          </button>
        </nav>

        {/* Action Controls */}
        <div className="nav-actions">
          {/* Health Indicator */}
          <div
            className="health-pill"
            title={
              health
                ? `DB: ${health.database?.status} | ML Model: ${health.ml_model?.status} (${health.ml_model?.version})`
                : 'Checking system health...'
            }
          >
            <span className={`health-dot ${isHealthy ? 'healthy' : 'degraded'}`} />
            <span>{isHealthy ? 'System Ready' : 'Degraded / Connecting'}</span>
          </div>

          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onRefresh}
            disabled={isRefreshing}
            title="Refresh dashboard data"
          >
            <RefreshCw size={14} className={isRefreshing ? 'spinner' : ''} />
            <span>Refresh</span>
          </button>

          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={onOpenCreateModal}
          >
            <Plus size={15} />
            <span>New Appointment</span>
          </button>
        </div>
      </div>
    </header>
  );
}
