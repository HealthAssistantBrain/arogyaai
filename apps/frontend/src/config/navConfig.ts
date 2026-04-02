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
    Shield,
    HelpCircle,
    Sparkles
} from 'lucide-react';
import { ROUTES } from '../router/routes';

export type NavItem = {
    label: string;
    icon?: any;
    path: string;
    children?: NavItem[];
};

export type NavSection = {
    section: string;
    items: NavItem[];
};

export const navConfig: NavSection[] = [
    {
        section: 'Intelligence',
        items: [
            { label: 'Dashboard', icon: LayoutDashboard, path: ROUTES.DASHBOARD },
            { label: 'AI Insights', icon: Brain, path: ROUTES.INSIGHTS },
            {
                label: 'Disease Simulator',
                icon: FlaskConical,
                path: ROUTES.SIMULATOR,
                children: [
                    // Assuming these routes will exist or map correctly to the simulator
                    { label: 'Risk Model', path: '/simulator/risk' },
                    { label: 'Environment', path: '/simulator/environment' },
                    { label: 'Lifestyle', path: '/simulator/lifestyle' }
                ]
            },
            { label: 'Recommendations', icon: ListChecks, path: ROUTES.RECOMMENDATIONS },
        ],
    },
    {
        section: 'History',
        items: [
            { label: 'Health Timeline', icon: History, path: ROUTES.TIMELINE },
            { label: 'Lab Results', icon: Activity, path: ROUTES.LAB_RESULTS },
            { label: 'Medical Reports', icon: FileText, path: ROUTES.MEDICAL_REPORTS },
            { label: 'Sleep Analysis', icon: Moon, path: ROUTES.SLEEP },
        ],
    },
    {
        section: 'Management',
        items: [
            { label: 'Upload Report', icon: Upload, path: ROUTES.UPLOAD },
            { label: 'AQI Monitor', icon: Wind, path: ROUTES.AQI_MONITOR },
            { label: 'Devices', icon: Smartphone, path: ROUTES.DEVICES },
            { label: 'Consultation', icon: User, path: ROUTES.CONSULTATION },
        ],
    },
    {
        section: 'System',
        items: [
            { label: 'Notifications', icon: Bell, path: ROUTES.NOTIFICATIONS },
            {
                label: 'Settings',
                icon: Settings,
                path: ROUTES.SETTINGS,
                children: [
                    { label: 'Profile', path: ROUTES.SETTINGS_PROFILE },
                    { label: 'Security', path: ROUTES.SETTINGS_SECURITY },
                    { label: 'Privacy', path: ROUTES.SETTINGS_PRIVACY },
                    { label: 'Notifications', path: ROUTES.SETTINGS_NOTIFICATIONS },
                    { label: 'Password', path: ROUTES.SETTINGS_PASSWORD },
                    { label: 'Delete Account', path: ROUTES.SETTINGS_DELETE },
                ]
            },
            { label: 'Log Out', icon: LogOut, path: ROUTES.LOGOUT },
        ],
    },
    {
        section: 'Support',
        items: [
            { label: 'Help Center', icon: HelpCircle, path: ROUTES.HELP },
            { label: 'What\'s New', icon: Sparkles, path: ROUTES.WHATS_NEW },
            { label: 'System Status', icon: Shield, path: ROUTES.STATUS },
        ]
    }
];
