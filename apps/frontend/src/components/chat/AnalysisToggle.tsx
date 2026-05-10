import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

type ExpertSection = {
  title?: string;
  content?: string;
};

type AnalysisToggleProps = {
  fullAnalysis?: string;
  sections?: ExpertSection[];
};

const AnalysisToggle = ({ fullAnalysis = '', sections = [] }: AnalysisToggleProps) => {
  const [open, setOpen] = useState(false);
  const hasSections = Array.isArray(sections) && sections.some((section) => section?.content);
  const hasContent = Boolean(fullAnalysis.trim()) || hasSections;

  if (!hasContent) return null;

  return (
    <div className="space-y-2">
      <button
        type="button"
        onClick={() => setOpen((current) => !current)}
        className="inline-flex items-center gap-1 text-sm font-semibold text-primary transition-opacity hover:opacity-80"
      >
        {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
        {open ? 'Hide full analysis' : 'Show full analysis ->'}
      </button>

      {open ? (
        <div className="max-h-80 overflow-y-auto rounded-2xl border border-slate-200 bg-slate-50/90 p-3 text-sm text-slate-700 dark:border-stroke dark:bg-[#120f22] dark:text-text-primary">
          {hasSections ? (
            <div className="space-y-4">
              {sections
                .filter((section) => section?.content)
                .map((section) => (
                  <section key={`${section.title}-${section.content?.slice(0, 24)}`} className="space-y-1">
                    {section.title ? (
                      <h4 className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500 dark:text-text-muted">
                        {section.title}
                      </h4>
                    ) : null}
                    <div className="whitespace-pre-wrap leading-relaxed">{section.content}</div>
                  </section>
                ))}
            </div>
          ) : (
            <div className="whitespace-pre-wrap leading-relaxed">{fullAnalysis}</div>
          )}
        </div>
      ) : null}
    </div>
  );
};

export default AnalysisToggle;
