// ── Centralized Sidebar Navigation Config (Step 7)
// Single source of truth — all pages import from here.
// DO NOT hardcode navigation strings in individual page files.
//
// Sidebar grouping:
//  1. Core
//  2. Intelligence
//  3. Health Data
//  4. Tools
//  5. Management
//  6. System

import {
  LayoutDashboard,
  Brain,
  FlaskConical,
  ListChecks,
  History,
  Activity,
  FileText,
  Moon,
  Upload,
  Wind,
  Smartphone,
  User,
  Bell,
  Settings,
  LogOut,
} from 'lucide-react'
import { ROUTES } from '../router/routes'

const sidebarConfig = [
  {
    section: 'Core',
    items: [
      { label: 'Dashboard',         icon: LayoutDashboard, path: ROUTES.DASHBOARD },
    ],
  },
  {
    section: 'Intelligence',
    items: [
      { label: 'AI Insights',        icon: Brain,           path: ROUTES.INSIGHTS },
      { label: 'Disease Simulator',  icon: FlaskConical,    path: ROUTES.SIMULATOR },
      { label: 'Recommendations',    icon: ListChecks,      path: ROUTES.RECOMMENDATIONS },
    ],
  },
  {
    section: 'Health Data',
    items: [
      { label: 'Health Timeline',    icon: History,         path: ROUTES.TIMELINE },
      { label: 'Lab Results',        icon: Activity,        path: ROUTES.LAB_RESULTS },
      { label: 'Medical Reports',    icon: FileText,        path: ROUTES.MEDICAL_REPORTS },
      { label: 'Sleep Analysis',     icon: Moon,            path: ROUTES.SLEEP },
    ],
  },
  {
    section: 'Tools',
    items: [
      { label: 'Upload Report',      icon: Upload,          path: ROUTES.UPLOAD },
      { label: 'AQI Monitor',        icon: Wind,            path: ROUTES.AQI_MONITOR },
    ],
  },
  {
    section: 'Management',
    items: [
      { label: 'Device Manager',     icon: Smartphone,      path: ROUTES.DEVICES },
      { label: 'Consultation',       icon: User,            path: ROUTES.CONSULTATION },
    ],
  },
  {
    section: 'System',
    items: [
      { label: 'Notifications',      icon: Bell,            path: ROUTES.NOTIFICATIONS },
      { label: 'Settings',           icon: Settings,        path: ROUTES.SETTINGS },
      { label: 'Log Out',            icon: LogOut,          path: ROUTES.LOGOUT },
    ],
  },
]

export default sidebarConfig
