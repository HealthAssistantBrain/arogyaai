import api from '../lib/axios';

const unwrap = (response) => response?.data?.data ?? response?.data ?? {};

export const fetchDoctorPatients = async () => {
  const response = await api.get('/doctor/patients');
  return unwrap(response);
};

export const fetchDoctorPatientDetail = async (patientId) => {
  const response = await api.get(`/doctor/patient/${patientId}`);
  return unwrap(response);
};

export const fetchDoctorAlerts = async (limit = 80) => {
  const response = await api.get('/doctor/alerts', { params: { limit } });
  return unwrap(response);
};

export const markDoctorPatientReviewed = async (patientId) => {
  const response = await api.post(`/doctor/patient/${patientId}/reviewed`, {});
  return unwrap(response);
};

export const sendDoctorRecommendation = async (patientId, payload) => {
  const response = await api.post(`/doctor/patient/${patientId}/recommendation`, payload);
  return unwrap(response);
};

export const triggerDoctorFollowUp = async (patientId, payload = {}) => {
  const response = await api.post(`/doctor/patient/${patientId}/follow-up`, payload);
  return unwrap(response);
};
