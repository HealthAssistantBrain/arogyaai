import { useState } from 'react';
import api from '../../lib/axios';

export function MemoryPrivacyControls() {
  const [deleting, setDeleting] = useState(false);
  const [deleted, setDeleted] = useState(false);

  const handleDeleteAll = async () => {
    if (!window.confirm('This permanently deletes your AI memory history and resets personalization. Continue?')) {
      return;
    }
    setDeleting(true);
    try {
      await api.delete('/memory/delete-all');
      setDeleted(true);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="rounded-[1.8rem] border border-slate-200 bg-white/90 p-5 shadow-sm dark:border-stroke dark:bg-background/45">
      <p className="text-[11px] font-black uppercase tracking-[0.24em] text-text-muted">Memory & Privacy</p>
      <h3 className="mt-2 text-lg font-black tracking-tight text-slate-950 dark:text-text-primary">You stay in control of what Arya remembers</h3>
      <p className="mt-3 text-sm leading-relaxed text-slate-500 dark:text-text-secondary">
        Long-term memory helps the assistant keep continuity across sessions. You can wipe that personalized memory at any time.
      </p>
      {deleted ? (
        <div className="mt-4 rounded-2xl bg-emerald-50 px-4 py-3 text-sm font-semibold text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-300">
          All personalized memory has been deleted. Arya will start fresh.
        </div>
      ) : (
        <button
          type="button"
          onClick={handleDeleteAll}
          disabled={deleting}
          className="mt-5 rounded-2xl border border-red-200 px-4 py-3 text-sm font-black uppercase tracking-[0.18em] text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-red-500/20 dark:text-red-300 dark:hover:bg-red-500/10"
        >
          {deleting ? 'Deleting...' : 'Delete all AI memory'}
        </button>
      )}
    </div>
  );
}
