const DEBUG_NAMESPACE = '__AROGYAAI_ORCHESTRATION_LOGS__'

const isBrowser = () => typeof window !== 'undefined'

const getDebugSink = () => {
  if (!isBrowser()) return null

  if (!Array.isArray(window[DEBUG_NAMESPACE])) {
    window[DEBUG_NAMESPACE] = []
  }

  return window[DEBUG_NAMESPACE]
}

export const logOrchestration = (scope, event, payload = {}, level = 'debug') => {
  const entry = {
    scope,
    event,
    timestamp: new Date().toISOString(),
    perfMs: typeof performance !== 'undefined' ? Math.round(performance.now()) : null,
    path: isBrowser() ? window.location.pathname : null,
    ...payload,
  }

  const sink = getDebugSink()
  if (sink) {
    sink.push(entry)
    if (sink.length > 500) {
      sink.splice(0, sink.length - 500)
    }
  }

  const logger =
    level === 'warn'
      ? console.warn.bind(console)
      : level === 'info'
        ? console.info.bind(console)
        : console.debug.bind(console)

  logger(`[orch:${scope}] ${event}`, entry)
  return entry
}
