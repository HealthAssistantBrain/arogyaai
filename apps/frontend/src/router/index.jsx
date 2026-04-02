import { lazy, Suspense } from 'react'
import {
  Routes, Route, Navigate,
  useLocation
} from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'
import { ROUTES } from './routes'
import AuthGuard from '../components/guards/AuthGuard'
import OnboardingGuard from '../components/guards/OnboardingGuard'
import GuestGuard from '../components/guards/GuestGuard'
import ActiveOnboardingGuard from '../components/guards/ActiveOnboardingGuard'
import LoadingScreen from '../pages/LoadingScreen'
import MainLayout from '../components/layout/MainLayout'

// ── lazy imports (all 59 pages) ──────────────────────────────────
const LandingPage = lazy(() => import('../pages/Landing'))
const Login = lazy(() => import('../pages/Login'))
const SignUp = lazy(() => import('../pages/Signup'))
const ForgotPassword = lazy(() => import('../pages/ForgotPassword'))
const EmailVerification = lazy(() => import('../pages/EmailVerification'))
const ResetPassword = lazy(() => import('../pages/ResetPassword'))
const AccountCreated = lazy(() => import('../pages/AccountCreated'))
const Step1BasicProfile = lazy(() => import('../pages/Onboarding'))
const Step2MedHistory = lazy(() => import('../pages/MedicalHistory'))
const Step3Lifestyle = lazy(() => import('../pages/Lifestyle'))
const Step4DeviceConnect = lazy(() => import('../pages/DeviceConnection'))
const OnboardingSummary = lazy(() => import('../pages/OnboardingSummary'))
const OnboardingCompletion = lazy(() => import('../pages/OnboardingCompletion'))
const MainDashboard = lazy(() => import('../pages/Dashboard'))
const DashboardAltView = lazy(() => import('../pages/DashboardAlternate'))
const AIHealthInsights = lazy(() => import('../pages/AIInsights'))
const AIInsightsDesktop = lazy(() => import('../pages/AIInsightsDesktop'))
const DiseaseSimulator = lazy(() => import('../pages/Simulate'))
const HealthTimeline = lazy(() => import('../pages/Timeline'))
const RiskExplanation = lazy(() => import('../pages/RiskExplanation'))
const PreventiveRecs = lazy(() => import('../pages/PreventiveRecommendations'))
const AIRiskReport = lazy(() => import('../pages/AIRiskReport'))
const AQIMonitor = lazy(() => import('../pages/AQIMonitor'))
const LabTestResults = lazy(() => import('../pages/LabResults'))
const MedicalReports = lazy(() => import('../pages/Reports'))
const SleepAnalysis = lazy(() => import('../pages/SleepAnalysis'))
const DeviceManager = lazy(() => import('../pages/DeviceManagement'))
const DeviceSettings = lazy(() => import('../pages/DeviceSettings'))
const UploadMedicalReport = lazy(() => import('../pages/UploadReport'))
const ReportProcessing = lazy(() => import('../pages/ReportProcessing'))
const UploadSuccess = lazy(() => import('../pages/UploadSuccess'))
const BookConsultation = lazy(() => import('../pages/BookConsultation'))
const DoctorProfile = lazy(() => import('../pages/DoctorProfile'))
const AppointmentConfirm = lazy(() => import('../pages/AppointmentConfirmation'))
const ConsultationHistory = lazy(() => import('../pages/ConsultationHistory'))
const SettingsHub = lazy(() => import('../pages/SettingsHub'))
const UserProfile = lazy(() => import('../pages/UserProfile'))
const SecurityAudit = lazy(() => import('../pages/SecurityAudit'))
const DataPrivacy = lazy(() => import('../pages/DataPrivacySettings'))
const NotificationSettings = lazy(() => import('../pages/NotificationSettings'))
const ChangePassword = lazy(() => import('../pages/ChangePassword'))
const DeleteAccount = lazy(() => import('../pages/DeleteAccount'))
const LogoutConfirmation = lazy(() => import('../pages/LogoutConfirmation'))
const NotificationCentre = lazy(() => import('../pages/NotificationCentre'))
const NotificationHistory = lazy(() => import('../pages/NotificationHistory'))
const AlertDetails = lazy(() => import('../pages/AlertDetails'))
const EmergencyAlert = lazy(() => import('../pages/EmergencyAlert'))
const HelpCenterHome = lazy(() => import('../pages/HelpCenterHome'))
const HelpCenterSearch = lazy(() => import('../pages/HelpCenterSearchResults'))
const HelpCenterArticle = lazy(() => import('../pages/HelpCenterArticle'))
const TermsOfService = lazy(() => import('../pages/TermsOfService'))
const PrivacyPolicy = lazy(() => import('../pages/PrivacyPolicy'))
const DataConsent = lazy(() => import('../pages/DataConsent'))
const SystemStatus = lazy(() => import('../pages/SystemStatus'))
const WhatsNew = lazy(() => import('../pages/WhatsNew'))
const NotFound404 = lazy(() => import('../pages/NotFound'))
const ServerError500 = lazy(() => import('../pages/ServerError'))
const MaintenancePage = lazy(() => import('../pages/SystemMaintenance'))

export default function AppRouter() {
  const location = useLocation()

  return (
    <Suspense fallback={<LoadingScreen />}>
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>

          {/* ── PUBLIC — no guard ─────────────────────────────── */}
          <Route path={ROUTES.HOME} element={<LandingPage />} />
          <Route path={ROUTES.TERMS} element={<TermsOfService />} />
          <Route path={ROUTES.PRIVACY} element={<PrivacyPolicy />} />
          <Route path={ROUTES.DATA_CONSENT} element={<DataConsent />} />
          <Route path={ROUTES.NOT_FOUND} element={<NotFound404 />} />
          <Route path={ROUTES.SERVER_ERROR} element={<ServerError500 />} />
          <Route path={ROUTES.MAINTENANCE} element={<MaintenancePage />} />

          {/* ── GUEST ONLY — redirect auth users to dashboard ─── */}
          <Route element={<GuestGuard />}>
            <Route path={ROUTES.LOGIN} element={<Login />} />
            <Route path={ROUTES.SIGNUP} element={<SignUp />} />
            <Route path={ROUTES.FORGOT_PASSWORD} element={<ForgotPassword />} />
            <Route path={ROUTES.RESET_PASSWORD} element={<ResetPassword />} />
          </Route>

          {/* ── AUTH REQUIRED ─────────────────────────────────── */}
          <Route element={<AuthGuard />}>

            {/* CRITICAL: onboarding steps are INSIDE AuthGuard   */}
            {/* but OUTSIDE OnboardingGuard — if they were inside  */}
            {/* OnboardingGuard they would trigger infinite loop   */}
            <Route path={ROUTES.EMAIL_VERIFICATION} element={<EmailVerification />} />
            <Route path={ROUTES.ACCOUNT_CREATED} element={<AccountCreated />} />

            {/* ── ACTIVE ONBOARDING REQUIRED (AND NOT FINISHED) ─ */}
            <Route element={<ActiveOnboardingGuard />}>
              <Route path={ROUTES.ONBOARDING_STEP_1} element={<Step1BasicProfile />} />
              <Route path={ROUTES.ONBOARDING_STEP_2} element={<Step2MedHistory />} />
              <Route path={ROUTES.ONBOARDING_STEP_3} element={<Step3Lifestyle />} />
              <Route path={ROUTES.ONBOARDING_STEP_4} element={<Step4DeviceConnect />} />
              <Route path={ROUTES.ONBOARDING_SUMMARY} element={<OnboardingSummary />} />
              <Route path={ROUTES.ONBOARDING_COMPLETION} element={<OnboardingCompletion />} />
            </Route>

            {/* ── ONBOARDING COMPLETE REQUIRED ─────────────────── */}
            <Route element={<OnboardingGuard />}>
              <Route element={<MainLayout />}>
                <Route path={ROUTES.DASHBOARD} element={<MainDashboard />} />
                <Route path={ROUTES.DASHBOARD_ALT} element={<DashboardAltView />} />
                <Route path={`${ROUTES.INSIGHTS}/*`} element={<AIHealthInsights />} />
                <Route path={`${ROUTES.INSIGHTS_DESKTOP}/*`} element={<AIInsightsDesktop />} />
                <Route path={`${ROUTES.SIMULATOR}/*`} element={<DiseaseSimulator />} />
                <Route path={ROUTES.TIMELINE} element={<HealthTimeline />} />
                <Route path={ROUTES.RISK_EXPLANATION} element={<RiskExplanation />} />
                <Route path={ROUTES.RECOMMENDATIONS} element={<PreventiveRecs />} />
                <Route path={ROUTES.RISK_REPORT} element={<AIRiskReport />} />
                <Route path={ROUTES.AQI_MONITOR} element={<AQIMonitor />} />
                <Route path={ROUTES.LAB_RESULTS} element={<LabTestResults />} />
                <Route path={ROUTES.MEDICAL_REPORTS} element={<MedicalReports />} />
                <Route path={ROUTES.SLEEP} element={<SleepAnalysis />} />
                <Route path={ROUTES.DEVICES} element={<DeviceManager />} />
                <Route path={ROUTES.DEVICE_SETTINGS} element={<DeviceSettings />} />
                <Route path={ROUTES.UPLOAD} element={<UploadMedicalReport />} />
                <Route path={ROUTES.REPORT_PROCESSING} element={<ReportProcessing />} />
                <Route path={ROUTES.UPLOAD_SUCCESS} element={<UploadSuccess />} />
                <Route path={ROUTES.CONSULTATION} element={<BookConsultation />} />
                <Route path={ROUTES.DOCTOR_PROFILE} element={<DoctorProfile />} />
                <Route path={ROUTES.APPOINTMENT_CONFIRM} element={<AppointmentConfirm />} />
                <Route path={ROUTES.CONSULTATION_HISTORY} element={<ConsultationHistory />} />
                <Route path={ROUTES.SETTINGS} element={<SettingsHub />} />
                <Route path={ROUTES.SETTINGS_PROFILE} element={<UserProfile />} />
                <Route path={ROUTES.SETTINGS_SECURITY} element={<SecurityAudit />} />
                <Route path={ROUTES.SETTINGS_PRIVACY} element={<DataPrivacy />} />
                <Route path={ROUTES.SETTINGS_NOTIFICATIONS} element={<NotificationSettings />} />
                <Route path={ROUTES.SETTINGS_PASSWORD} element={<ChangePassword />} />
                <Route path={ROUTES.SETTINGS_DELETE} element={<DeleteAccount />} />
                <Route path={ROUTES.LOGOUT} element={<LogoutConfirmation />} />
                <Route path={ROUTES.NOTIFICATIONS} element={<NotificationCentre />} />
                <Route path={ROUTES.NOTIFICATIONS_HISTORY} element={<NotificationHistory />} />
                <Route path={ROUTES.ALERT_DETAILS} element={<AlertDetails />} />
                <Route path={ROUTES.EMERGENCY_ALERT} element={<EmergencyAlert />} />
                <Route path={ROUTES.WHATS_NEW} element={<WhatsNew />} />
                {/* Help Center/Status inside MainLayout so sidebar renders */}
                <Route path={ROUTES.HELP} element={<HelpCenterHome />} />
                <Route path={ROUTES.HELP_SEARCH} element={<HelpCenterSearch />} />
                <Route path={ROUTES.HELP_ARTICLE} element={<HelpCenterArticle />} />
                <Route path={ROUTES.STATUS} element={<SystemStatus />} />
                {/* Security Audit is also accessible via /settings/security-audit */}
                <Route path={ROUTES.SECURITY_AUDIT} element={<SecurityAudit />} />
              </Route>
            </Route>
          </Route>

          {/* ── CATCH ALL — must be absolute last ──────────────── */}
          <Route
            path="*"
            element={<Navigate to={ROUTES.NOT_FOUND} replace />}
          />

        </Routes>
      </AnimatePresence>
    </Suspense>
  )
}
