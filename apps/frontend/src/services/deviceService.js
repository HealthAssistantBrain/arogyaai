/**
 * deviceService.js
 *
 * Shared Google Fit connection utility.
 * Uses the pre-configured apiClient (which auto-injects the auth token
 * and the correct API base URL from env), so any component can call
 * connectGoogleFit() without duplicating auth / URL logic.
 */

import { fetchGoogleFitConnect } from '../lib/googleFitApi';
import toast from 'react-hot-toast';

/**
 * Initiates the Google Fit OAuth flow.
 * Redirects the browser to Google's consent screen on success.
 *
 * @param {object} [options]
 * @param {string} [options.redirectPath] - The path the OAuth callback should
 *   redirect back to after completing the flow (default: current pathname).
 */
export async function connectGoogleFit({ redirectPath } = {}) {
    console.log('Redirecting to Google Fit OAuth...');
    try {
        const result = await fetchGoogleFitConnect({
            timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
            redirectPath: redirectPath || window.location.pathname,
        });

        if (result?.auth_url) {
            window.location.href = result.auth_url;
        } else {
            toast.error('Failed to initiate Google Fit connection');
        }
    } catch (err) {
        console.error('[deviceService] connectGoogleFit error:', err);
        toast.error('An error occurred connecting to Google Fit');
    }
}
