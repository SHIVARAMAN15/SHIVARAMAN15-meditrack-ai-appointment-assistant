import axios from 'axios';

// Centralized Axios client targeting Vite proxy (/api)
const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// Response interceptor for consistent error normalization
api.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = 'An unexpected error occurred.';
    let code = 'UNKNOWN_ERROR';

    if (error.response) {
      const data = error.response.data;
      if (data && data.error) {
        message = data.error.message || message;
        code = data.error.code || code;
      } else if (data && data.message) {
        message = data.message;
      }
    } else if (error.request) {
      message = 'Cannot connect to MediTrack AI backend server. Please verify the Flask service is running.';
      code = 'NETWORK_ERROR';
    }

    const enhancedError = new Error(message);
    enhancedError.code = code;
    enhancedError.original = error;
    return Promise.reject(enhancedError);
  }
);

// Health & System Readiness
export const getHealth = async () => {
  const { data } = await api.get('/health');
  return data;
};

// Analytics & KPIs
export const getDashboardSummary = async () => {
  const { data } = await api.get('/analytics/summary');
  return data;
};

export const getAnalyticsTrends = async () => {
  const { data } = await api.get('/analytics/trends');
  return data;
};

export const getInteractionLogs = async (params = {}) => {
  const { data } = await api.get('/logs', { params });
  return data;
};

// Appointments API
export const getAppointments = async (params = {}) => {
  const { data } = await api.get('/appointments', { params });
  return data;
};

export const getAppointment = async (idOrCode) => {
  const { data } = await api.get(`/appointments/${idOrCode}`);
  return data;
};

export const createAppointment = async (payload) => {
  const { data } = await api.post('/appointments', payload);
  return data;
};

export const rescheduleAppointment = async (idOrCode, payload) => {
  const { data } = await api.post(`/appointments/${idOrCode}/reschedule`, payload);
  return data;
};

export const cancelAppointment = async (idOrCode, payload) => {
  const { data } = await api.post(`/appointments/${idOrCode}/cancel`, payload);
  return data;
};

export const patchAppointment = async (idOrCode, payload) => {
  const { data } = await api.patch(`/appointments/${idOrCode}`, payload);
  return data;
};

// ML Predictions API
export const getAppointmentPrediction = async (appointmentId) => {
  const { data } = await api.get(`/predictions/${appointmentId}`);
  return data;
};

export const refreshAppointmentPrediction = async (appointmentId) => {
  const { data } = await api.post(`/predictions/${appointmentId}/refresh`);
  return data;
};

export const getPredictionsList = async (params = {}) => {
  const { data } = await api.get('/predictions', { params });
  return data;
};

// Reminders API
export const getReminderRecommendations = async (includeMediumRisk = true) => {
  const { data } = await api.get('/reminders/recommendations', {
    params: { include_medium_risk: includeMediumRisk },
  });
  return data;
};

export const sendSimulatedReminder = async (appointmentId, payload = {}) => {
  const { data } = await api.post(`/reminders/${appointmentId}/send`, payload);
  return data;
};

export const getRemindersList = async (params = {}) => {
  const { data } = await api.get('/reminders', { params });
  return data;
};

// Chatbot API
export const sendChatMessage = async (message, sessionId = 'staff_session') => {
  const { data } = await api.post('/chat', { message, session_id: sessionId });
  return data;
};

export default api;
