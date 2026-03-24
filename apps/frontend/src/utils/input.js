/**
 * Utility functions for ArogyaAI Frontend.
 */

export function safeInput(input) {
    const MAX_CHARS = 12000; // safe zone

    if (!input || typeof input !== 'string') {
        return input;
    }

    if (input.length > MAX_CHARS) {
        return input.slice(0, MAX_CHARS);
    }
    return input;
}
