type QuickRepliesProps = {
  replies?: string[];
  disabled?: boolean;
  onSelect: (reply: string) => void;
};

const QuickReplies = ({ replies = [], disabled = false, onSelect }: QuickRepliesProps) => {
  if (!replies.length) return null;

  return (
    <div className="flex flex-wrap gap-2 pt-1">
      {replies.map((reply) => (
        <button
          key={reply}
          type="button"
          disabled={disabled}
          onClick={() => onSelect(reply)}
          className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-60 dark:border-stroke dark:bg-white/5 dark:text-text-primary dark:hover:bg-white/10"
        >
          {reply}
        </button>
      ))}
    </div>
  );
};

export default QuickReplies;
