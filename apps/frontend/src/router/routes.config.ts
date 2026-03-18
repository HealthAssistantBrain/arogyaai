import { ComponentType, lazy } from 'react';

export interface RouteConfig {
  path: string;
  component: ComponentType<any>;
  guards: string[];
  public: boolean;
  module: string;
}

// Map the essential components. Real module structure to be integrated fully inside routing.
const Dashboard       = lazy(() => import('../pages/Dashboard'));
const Login           = lazy(() => import('../pages/Login'));
const Signup          = lazy(() => import('../pages/Signup'));
const Onboarding1     = lazy(() => import('../pages/onboarding/Step1'));
const SystemError     = lazy(() => import('../pages/SystemError').catch(() => ({ default: () => <div>System Error / Maintenance Mode</div> })));
const Landing         = lazy(() => import('../pages/Landing').catch(() => ({ default: () => <div>ArogyaAI Launching...</div> })));

export const ROUTES: RouteConfig[] = [
  { path: '/system/error', component: SystemError, guards: [], public: true, module: 'SYSTEM' },
  { path: '/maintenance', component: SystemError, guards: [], public: true, module: 'SYSTEM' },
  { path: '/', component: Landing, guards: [], public: true, module: 'PUBLIC' },
  { path: '/login', component: Login, guards: ['GUEST_GUARD'], public: true, module: 'AUTH' },
  { path: '/signup', component: Signup, guards: ['GUEST_GUARD'], public: true, module: 'AUTH' },
  { path: '/dashboard', component: Dashboard, guards: ['AUTH_GUARD', 'ONBOARDING_GUARD'], public: false, module: 'DASHBOARD' },
  { path: '/onboarding/step-1', component: Onboarding1, guards: ['AUTH_GUARD'], public: false, module: 'ONBOARDING' },
];
