import React, { useState, useEffect, useCallback } from 'react';
import Navbar from './components/Navbar';
import KpiCards from './components/KpiCards';
import AppointmentTable from './components/AppointmentTable';
import {
  CreateAppointmentModal,
  RescheduleModal,
  CancelModal,
  DetailPredictionModal,
} from './components/AppointmentModals';
import ReminderCenter from './components/ReminderCenter';
import AnalyticsCharts from './components/AnalyticsCharts';
import ChatbotDrawer from './components/ChatbotDrawer';
import Toast from './components/Toast';
import {
  getHealth,
  getDashboardSummary,
  getAnalyticsTrends,
  getAppointments,
  createAppointment,
  rescheduleAppointment,
  cancelAppointment,
  sendSimulatedReminder,
  refreshAppointmentPrediction,
  getReminderRecommendations,
} from './api/client';
import { AlertTriangle, Plus } from 'lucide-react';

export default function App() {
  // Navigation & Views
  const [activeTab, setActiveTab] = useState('dashboard'); // dashboard | appointments | reminders | analytics

  // Data State
  const [health, setHealth] = useState(null);
  const [summary, setSummary] = useState(null);
  const [trends, setTrends] = useState(null);
  const [appointments, setAppointments] = useState([]);
  const [totalAppointments, setTotalAppointments] = useState(0);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [perPage] = useState(12);

  // Filters
  const [filters, setFilters] = useState({
    search: '',
    department: '',
    status: '',
    risk_category: '',
  });

  // Reminders State
  const [recommendations, setRecommendations] = useState([]);
  const [includeMediumRisk, setIncludeMediumRisk] = useState(true);
  const [sendingReminderId, setSendingReminderId] = useState(null);

  // Loading & Action States
  const [initialLoading, setInitialLoading] = useState(true);
  const [tableLoading, setTableLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [submittingAction, setSubmittingAction] = useState(false);
  const [refreshingPrediction, setRefreshingPrediction] = useState(false);
  const [connectionError, setConnectionError] = useState(null);

  // Modals
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [rescheduleApt, setRescheduleApt] = useState(null);
  const [cancelApt, setCancelApt] = useState(null);
  const [detailApt, setDetailApt] = useState(null);

  // Toasts
  const [toasts, setToasts] = useState([]);

  const addToast = (type, message, title = '') => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, type, message, title }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  // Fetch Summary & Trends
  const loadOverviewData = useCallback(async () => {
    try {
      const [healthData, summaryData, trendsData] = await Promise.all([
        getHealth().catch(() => null),
        getDashboardSummary().catch(() => null),
        getAnalyticsTrends().catch(() => null),
      ]);
      setHealth(healthData);
      setSummary(summaryData);
      setTrends(trendsData);
      setConnectionError(null);
    } catch (err) {
      setConnectionError(err.message);
    }
  }, []);

  // Fetch Appointments
  const loadAppointments = useCallback(async (currPage = page, currFilters = filters) => {
    setTableLoading(true);
    try {
      const params = {
        page: currPage,
        per_page: perPage,
        search: currFilters.search || undefined,
        department: currFilters.department || undefined,
        status: currFilters.status || undefined,
        risk_category: currFilters.risk_category || undefined,
      };
      const res = await getAppointments(params);
      setAppointments(res.appointments || []);
      setTotalAppointments(res.total || 0);
      setPages(res.pages || 1);
      setPage(res.page || 1);
    } catch (err) {
      addToast('error', `Failed to load appointments: ${err.message}`, 'Network Error');
    } finally {
      setTableLoading(false);
    }
  }, [page, filters, perPage]);

  // Fetch Reminder Recommendations
  const loadRecommendations = useCallback(async (includeMed = includeMediumRisk) => {
    try {
      const res = await getReminderRecommendations(includeMed);
      setRecommendations(res.recommendations || []);
    } catch (err) {
      console.error('Error fetching recommendations:', err);
    }
  }, [includeMediumRisk]);

  // Initial Data Load
  useEffect(() => {
    const init = async () => {
      setInitialLoading(true);
      await Promise.all([loadOverviewData(), loadAppointments(1, filters), loadRecommendations(includeMediumRisk)]);
      setInitialLoading(false);
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Filter change handler
  const handleFilterChange = (key, value) => {
    const updated = { ...filters, [key]: value };
    setFilters(updated);
    setPage(1);
    loadAppointments(1, updated);
  };

  // Refresh all dashboard metrics and appointments
  const refreshAll = async () => {
    setIsRefreshing(true);
    await Promise.all([
      loadOverviewData(),
      loadAppointments(page, filters),
      loadRecommendations(includeMediumRisk),
    ]);
    setIsRefreshing(false);
    addToast('info', 'Dashboard metrics synchronized with clinic database.', 'Data Refreshed');
  };

  // Appointment Mutations
  const handleCreateAppointment = async (payload) => {
    setSubmittingAction(true);
    try {
      const res = await createAppointment(payload);
      addToast('success', res.message || 'Appointment created successfully.', 'Appointment Scheduled');
      setCreateModalOpen(false);
      refreshAll();
    } catch (err) {
      addToast('error', err.message, 'Failed to Create Appointment');
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleRescheduleAppointment = async (aptId, payload) => {
    setSubmittingAction(true);
    try {
      const res = await rescheduleAppointment(aptId, payload);
      addToast('success', res.message || 'Appointment slot updated.', 'Rescheduled Successfully');
      setRescheduleApt(null);
      refreshAll();
    } catch (err) {
      addToast('error', err.message, 'Reschedule Rejected');
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleCancelAppointment = async (aptId, payload) => {
    setSubmittingAction(true);
    try {
      const res = await cancelAppointment(aptId, payload);
      addToast('success', res.message || 'Appointment cancelled.', 'Cancellation Confirmed');
      setCancelApt(null);
      refreshAll();
    } catch (err) {
      addToast('error', err.message, 'Cancellation Failed');
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleSendReminder = async (aptId) => {
    setSendingReminderId(aptId);
    try {
      const res = await sendSimulatedReminder(aptId, { channel: 'simulated_sms' });
      addToast('success', res.message || 'Simulated reminder sent to patient.', 'Reminder Dispatched');
      loadRecommendations(includeMediumRisk);
      loadOverviewData();
      loadAppointments(page, filters);
    } catch (err) {
      addToast('error', err.message, 'Reminder Dispatch Error');
    } finally {
      setSendingReminderId(null);
    }
  };

  const handleRefreshPrediction = async (aptId) => {
    setRefreshingPrediction(true);
    try {
      const res = await refreshAppointmentPrediction(aptId);
      addToast('success', 'ML prediction score updated using latest patient history.', 'Score Recalculated');
      // Update modal view
      if (detailApt && detailApt.id === aptId) {
        setDetailApt({
          ...detailApt,
          latest_prediction: res.prediction,
        });
      }
      loadAppointments(page, filters);
      loadOverviewData();
    } catch (err) {
      addToast('error', err.message, 'Prediction Error');
    } finally {
      setRefreshingPrediction(false);
    }
  };

  return (
    <div className="app-container">
      {/* Toast Notification Container */}
      <Toast toasts={toasts} onDismiss={removeToast} />

      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        health={health}
        onRefresh={refreshAll}
        onOpenCreateModal={() => setCreateModalOpen(true)}
        isRefreshing={isRefreshing}
      />

      {/* Connection Error Alert */}
      {connectionError && (
        <div style={{ background: 'var(--danger-light)', padding: '12px 24px', color: 'var(--danger-dark)', display: 'flex', alignItems: 'center', gap: '10px', fontSize: '0.875rem' }}>
          <AlertTriangle size={18} />
          <span>{connectionError}</span>
        </div>
      )}

      {/* Main Workspace */}
      <main className="main-content">
        {/* KPI Cards (Always visible on dashboard, or accessible at glance) */}
        <KpiCards summary={summary} loading={initialLoading} />

        {/* Tab View 1: DASHBOARD OVERVIEW */}
        {activeTab === 'dashboard' && (
          <>
            {/* Quick action bar */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
              <div>
                <h1 style={{ fontSize: '1.4rem', margin: 0, fontWeight: 700, color: 'var(--neutral-900)' }}>
                  Clinical Attendance Intelligence
                </h1>
                <p style={{ fontSize: '0.85rem', color: 'var(--neutral-500)' }}>
                  Real-time schedule monitoring, automated attendance probability scoring, and proactive patient reminders
                </p>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setCreateModalOpen(true)}
                >
                  <Plus size={16} />
                  <span>Book Appointment</span>
                </button>
              </div>
            </div>

            {/* Overview Charts */}
            <AnalyticsCharts trends={trends} loading={initialLoading} />

            {/* High-Risk AI Follow-Up Quick List */}
            {recommendations.length > 0 && (
              <div className="panel">
                <div className="panel-header">
                  <div className="panel-title">
                    <AlertTriangle size={18} style={{ color: 'var(--danger)' }} />
                    Immediate Reminder Recommendations ({recommendations.length})
                  </div>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setActiveTab('reminders')}
                  >
                    View All in Reminder Center &rarr;
                  </button>
                </div>
                <div className="panel-body" style={{ padding: '14px 20px' }}>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
                    {recommendations.slice(0, 3).map((rec) => (
                      <div
                        key={rec.appointment_id}
                        style={{
                          padding: '12px 14px',
                          background: 'var(--neutral-50)',
                          border: '1px solid var(--border-color)',
                          borderRadius: 'var(--radius-md)',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: '6px',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span style={{ fontWeight: 600, color: 'var(--neutral-900)' }}>
                            {rec.patient_name}
                          </span>
                          <span className={`badge badge-risk-${rec.risk_category}`}>
                            {Math.round(rec.no_show_probability * 100)}% risk
                          </span>
                        </div>
                        <div style={{ fontSize: '0.78rem', color: 'var(--neutral-500)' }}>
                          {rec.department} &bull; {new Date(rec.appointment_datetime).toLocaleDateString()}
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '4px' }}>
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            disabled={!rec.can_send || sendingReminderId === rec.appointment_id}
                            onClick={() => handleSendReminder(rec.appointment_id)}
                          >
                            <span>Send Simulated SMS</span>
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Appointments Table */}
            <AppointmentTable
              appointments={appointments}
              total={totalAppointments}
              page={page}
              pages={pages}
              perPage={perPage}
              filters={filters}
              onFilterChange={handleFilterChange}
              onPageChange={(p) => {
                setPage(p);
                loadAppointments(p, filters);
              }}
              loading={tableLoading}
              onOpenDetailModal={(apt) => setDetailApt(apt)}
              onOpenRescheduleModal={(apt) => setRescheduleApt(apt)}
              onOpenCancelModal={(apt) => setCancelApt(apt)}
              onSendReminder={handleSendReminder}
            />
          </>
        )}

        {/* Tab View 2: FULL APPOINTMENTS TABLE */}
        {activeTab === 'appointments' && (
          <AppointmentTable
            appointments={appointments}
            total={totalAppointments}
            page={page}
            pages={pages}
            perPage={perPage}
            filters={filters}
            onFilterChange={handleFilterChange}
            onPageChange={(p) => {
              setPage(p);
              loadAppointments(p, filters);
            }}
            loading={tableLoading}
            onOpenDetailModal={(apt) => setDetailApt(apt)}
            onOpenRescheduleModal={(apt) => setRescheduleApt(apt)}
            onOpenCancelModal={(apt) => setCancelApt(apt)}
            onSendReminder={handleSendReminder}
          />
        )}

        {/* Tab View 3: REMINDER RECOMMENDATION CENTER */}
        {activeTab === 'reminders' && (
          <ReminderCenter
            recommendations={recommendations}
            loading={initialLoading}
            includeMediumRisk={includeMediumRisk}
            onToggleMediumRisk={(val) => {
              setIncludeMediumRisk(val);
              loadRecommendations(val);
            }}
            onSendReminder={handleSendReminder}
            onRefresh={() => loadRecommendations(includeMediumRisk)}
            sendingId={sendingReminderId}
          />
        )}

        {/* Tab View 4: ANALYTICS & TRENDS */}
        {activeTab === 'analytics' && (
          <AnalyticsCharts trends={trends} loading={initialLoading} />
        )}
      </main>

      {/* Floating Staff Assistant Chatbot */}
      <ChatbotDrawer onActionTriggered={() => refreshAll()} />

      {/* Modals */}
      <CreateAppointmentModal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        onSubmit={handleCreateAppointment}
        submitting={submittingAction}
      />

      <RescheduleModal
        isOpen={Boolean(rescheduleApt)}
        appointment={rescheduleApt}
        onClose={() => setRescheduleApt(null)}
        onSubmit={handleRescheduleAppointment}
        submitting={submittingAction}
      />

      <CancelModal
        isOpen={Boolean(cancelApt)}
        appointment={cancelApt}
        onClose={() => setCancelApt(null)}
        onSubmit={handleCancelAppointment}
        submitting={submittingAction}
      />

      <DetailPredictionModal
        isOpen={Boolean(detailApt)}
        appointment={detailApt}
        onClose={() => setDetailApt(null)}
        onRefreshPrediction={handleRefreshPrediction}
        refreshingPrediction={refreshingPrediction}
      />
    </div>
  );
}
