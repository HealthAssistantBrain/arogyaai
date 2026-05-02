import { createElement } from 'react';
import { Activity, BookOpen, ClipboardList, ShieldCheck, Stethoscope } from 'lucide-react';
import { normalizeClinicalCard } from '../../lib/clinicalCards';

const toneStyles = {
  high: {
    badge: 'bg-rose-50 text-rose-700 ring-1 ring-rose-200 dark:bg-rose-500/15 dark:text-rose-200 dark:ring-rose-500/25',
    bar: 'bg-rose-500',
    rail: 'bg-rose-100 dark:bg-rose-950/40',
  },
  moderate: {
    badge: 'bg-amber-50 text-amber-700 ring-1 ring-amber-200 dark:bg-amber-500/15 dark:text-amber-200 dark:ring-amber-500/25',
    bar: 'bg-amber-500',
    rail: 'bg-amber-100 dark:bg-amber-950/40',
  },
  low: {
    badge: 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 dark:bg-emerald-500/15 dark:text-emerald-200 dark:ring-emerald-500/25',
    bar: 'bg-emerald-500',
    rail: 'bg-emerald-100 dark:bg-emerald-950/40',
  },
};

const Section = ({ icon, title, children }) => {
  const iconNode = createElement(icon, { size: 16, className: 'text-slate-400 dark:text-slate-500' });

  return (
    <section className="border-t border-slate-200 pt-5 dark:border-white/10">
      <div className="mb-3 flex items-center gap-2">
        {iconNode}
        <h3 className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-500 dark:text-slate-400">
          {title}
        </h3>
      </div>
      {children}
    </section>
  );
};

const BulletList = ({ items, emptyText }) => (
  items.length > 0 ? (
    <ul className="space-y-2 text-sm font-medium leading-relaxed text-slate-700 dark:text-slate-300">
      {items.map((item) => (
        <li key={item} className="grid grid-cols-[0.45rem_1fr] gap-3">
          <span className="mt-2 size-1.5 rounded-full bg-slate-400 dark:bg-slate-500" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  ) : (
    <p className="text-sm font-medium leading-relaxed text-slate-500 dark:text-slate-400">{emptyText}</p>
  )
);

const ClinicalInsightCard = ({ card, fallback, className = '' }) => {
  const normalized = normalizeClinicalCard(card, fallback);
  const tone = toneStyles[normalized.tone] || toneStyles.low;
  const references = normalized.references.length ? normalized.references : ['ArogyaAI clinical model output'];

  return (
    <article className={`rounded-lg border border-slate-200 bg-white p-6 shadow-sm dark:border-white/10 dark:bg-[#1a1433] ${className}`}>
      <div className="flex flex-col gap-5 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <p className="text-[11px] font-black uppercase tracking-[0.18em] text-slate-400 dark:text-slate-500">
            Clinical Condition
          </p>
          <h2 className="mt-2 text-2xl font-black tracking-tight text-[#13082a] dark:text-white">
            {normalized.condition}
            <span className="ml-2 align-middle text-sm font-black text-slate-400 dark:text-slate-500">
              {normalized.icdCode}
            </span>
          </h2>
        </div>

        <div className="flex flex-wrap gap-2">
          <span className={`inline-flex items-center rounded-full px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em] ${tone.badge}`}>
            {normalized.riskLevel} risk
          </span>
          <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-slate-700 ring-1 ring-slate-200 dark:bg-white/5 dark:text-slate-200 dark:ring-white/10">
            {normalized.confidencePercent.toFixed(1)}% confidence
          </span>
        </div>
      </div>

      <div className="mt-6">
        <div className="mb-2 flex items-center justify-between text-[10px] font-black uppercase tracking-[0.18em] text-slate-400 dark:text-slate-500">
          <span>Confidence</span>
          <span>{normalized.confidenceLabel}</span>
        </div>
        <div className={`h-2.5 overflow-hidden rounded-full ${tone.rail}`}>
          <div
            className={`h-full rounded-full ${tone.bar}`}
            style={{ width: `${Math.max(4, normalized.confidencePercent)}%` }}
          />
        </div>
      </div>

      <div className="mt-6 space-y-5">
        <Section icon={Stethoscope} title="Clinical Insight">
          <p className="text-sm font-semibold leading-relaxed text-slate-700 dark:text-slate-200">
            {normalized.clinicalInsight}
          </p>
        </Section>

        <Section icon={Activity} title="Symptoms">
          <BulletList items={normalized.symptoms} emptyText="No symptom inference is available from the current clinical payload." />
        </Section>

        <Section icon={ClipboardList} title="Recommendations">
          <BulletList items={normalized.recommendations} emptyText="No recommendations were returned for this condition." />
        </Section>

        <Section icon={BookOpen} title="References">
          <div className="flex flex-wrap gap-2">
            {references.map((reference) => (
              <span
                key={reference}
                className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-slate-50 px-2.5 py-1 text-[11px] font-bold text-slate-600 dark:border-white/10 dark:bg-white/[0.04] dark:text-slate-300"
              >
                <ShieldCheck size={12} />
                {reference}
              </span>
            ))}
          </div>
        </Section>
      </div>
    </article>
  );
};

export default ClinicalInsightCard;
