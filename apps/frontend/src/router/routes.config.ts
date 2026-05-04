import { ComponentType, lazy } from 'react';

export interface RouteConfig {
  path: string;
  component: ComponentType<any>;
  guards: string[];
  public: boolean;
  module: string;
}

// Map the essential components. Real module structure to be integrated fully inside routing.
const Dashboard = lazy(() => import('../pages/Dashboard'));
const Login = lazy(() => import('../pages/Login'));
const Signup = lazy(() => import('../pages/Signup'));
const Onboarding4 = lazy(() => import('../pages/onboarding/Step4'));
const EmailVerification = lazy(() => import('../pages/EmailVerification'));
const SystemError = lazy(() => import('../pages/SystemError').catch(() => ({ default: () => 'System Error / Maintenance Mode' } as any)));
const Landing = lazy(() => import('../pages/Landing').catch(() => ({ default: () => 'ArogyaAI Launching...' } as any)));

export const ROUTES: RouteConfig[] = [
  { path: '/system/error', component: SystemError, guards: [], public: true, module: 'SYSTEM' },
  { path: '/maintenance', component: SystemError, guards: [], public: true, module: 'SYSTEM' },
  { path: '/', component: Landing, guards: [], public: true, module: 'PUBLIC' },
  { path: '/login', component: Login, guards: ['GUEST_GUARD'], public: true, module: 'AUTH' },
  { path: '/signup', component: Signup, guards: ['GUEST_GUARD'], public: true, module: 'AUTH' },
  // EMAIL_VERIFICATION: only requires authentication — never apply EMAIL_GUARD here (would loop)
  { path: '/email-verification', component: EmailVerification, guards: ['AUTH_GUARD'], public: false, module: 'AUTH' },
  // DASHBOARD: requires auth + email verified + onboarding done
  { path: '/onboarding', component: Onboarding4, guards: ['AUTH_GUARD', 'EMAIL_GUARD'], public: false, module: 'ONBOARDING' },
  { path: '/dashboard', component: Dashboard, guards: ['AUTH_GUARD', 'EMAIL_GUARD', 'ONBOARDING_GUARD'], public: false, module: 'DASHBOARD' },
  { path: '/onboarding/step-4', component: Onboarding4, guards: ['AUTH_GUARD', 'EMAIL_GUARD'], public: false, module: 'ONBOARDING' },
];
