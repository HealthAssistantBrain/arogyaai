import {
    LayoutDashboard,
    Brain,
    FlaskConical,
    ListChecks,
    History,
    Activity,
    FileText,
    Moon,
    Smartphone,
    Bell,
    Settings,
    HelpCircle,
    Wind,
    Stethoscope
} from 'lucide-react';
import { ROUTES } from '../router/routes';

export type NavItem = {
    label: string;
    icon?: any;
    path: string;
    roles?: string[];
    children?: NavItem[];
};

export type NavSection = {
    section: string;
    items: NavItem[];
};

export const navConfig: NavSection[] = [
    {
        section: '',
        items: [
            { label: 'Dashboard', icon: LayoutDashboard, path: ROUTES.DASHBOARD },
            { label: 'Doctor Monitor', icon: Stethoscope, path: ROUTES.DOCTOR_DASHBOARD, roles: ['doctor'] },
            { label: 'AI Insights', icon: Brain, path: ROUTES.INSIGHTS },
            { label: 'AI Risk Prediction', icon: Brain, path: ROUTES.RISK_PREDICTION },
            { label: 'Disease Simulator', icon: FlaskConical, path: ROUTES.SIMULATOR },
            { label: 'Recommendations', icon: ListChecks, path: ROUTES.RECOMMENDATIONS },
            { label: 'Health Timeline', icon: History, path: ROUTES.TIMELINE },
            { label: 'Lab Results', icon: Activity, path: ROUTES.LAB_RESULTS },
            { label: 'Medical Reports', icon: FileText, path: ROUTES.MEDICAL_REPORTS },
            { label: 'Sleep Analysis', icon: Moon, path: ROUTES.SLEEP },
            { label: 'Device Manager', icon: Smartphone, path: ROUTES.DEVICES },
            { label: 'AQI Monitor', icon: Wind, path: ROUTES.AQI_MONITOR },
        ],
    },
    {
        section: '',
        items: [
            { label: 'Notifications', icon: Bell, path: ROUTES.NOTIFICATIONS },
            { label: 'Settings', icon: Settings, path: ROUTES.SETTINGS },
            { label: 'Help Center', icon: HelpCircle, path: ROUTES.HELP },
        ]
    }
];
