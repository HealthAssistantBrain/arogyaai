import { Brain, Lightbulb, Shield } from "lucide-react";
import { useReveal } from "@/hooks/use-reveal";

export const SectionHeader = ({
  eyebrow,
  title,
  subtitle,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  subtitle?: string;
}) => {
  const { ref, visible } = useReveal();
  return (
    <div ref={ref} className={`max-w-2xl mx-auto text-center mb-16 ${visible ? "animate-fade-up" : "opacity-0"}`}>
      {eyebrow && (
        <div className="inline-flex items-center gap-2 glass rounded-full px-3 py-1 text-xs text-primary mb-4">
          {eyebrow}
        </div>
      )}
      <h2 className="font-display text-4xl md:text-5xl font-semibold tracking-tight">{title}</h2>
      {subtitle && <p className="mt-4 text-muted-foreground text-lg">{subtitle}</p>}
    </div>
  );
};

const features = [
  {
    icon: Brain,
    title: "Predict",
    desc: "ML-based disease risk detection for diabetes, cardiovascular conditions and more — trained on multi-modal health signals.",
    accent: "200 100% 60%",
    preview: (
      <svg viewBox="0 0 200 60" className="w-full h-14">
        {[12, 22, 18, 30, 26, 38, 32, 44, 40, 48].map((h, i) => (
          <rect
            key={i}
            x={i * 20 + 4}
            y={60 - h}
            width="12"
            height={h}
            rx="2"
            fill="url(#bar1)"
          />
        ))}
        <defs>
          <linearGradient id="bar1" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="hsl(200 100% 60%)" />
            <stop offset="100%" stopColor="hsl(200 100% 60% / 0.2)" />
          </linearGradient>
        </defs>
      </svg>
    ),
  },
  {
    icon: Lightbulb,
    title: "Explain",
    desc: "SHAP values and natural-language reasoning surface the exact factors driving each prediction — no black boxes.",
    accent: "265 85% 65%",
    preview: (
      <div className="space-y-1.5 mt-2">
        {[
          { l: "Glucose", v: 80 },
          { l: "Sleep", v: 55 },
          { l: "BMI", v: 35 },
        ].map((b) => (
          <div key={b.l} className="flex items-center gap-2 text-[10px]">
            <span className="w-12 text-muted-foreground">{b.l}</span>
            <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
              <div className="h-full" style={{ width: `${b.v}%`, background: "linear-gradient(90deg, hsl(265 85% 65%), hsl(200 100% 60%))" }} />
            </div>
          </div>
        ))}
      </div>
    ),
  },
  {
    icon: Shield,
    title: "Prevent",
    desc: "Personalized, evidence-backed lifestyle and clinical recommendations tailored to your trends and risk profile.",
    accent: "180 100% 55%",
    preview: (
      <svg viewBox="0 0 200 60" className="w-full h-14">
        <path
          d="M0,40 C30,42 50,20 80,22 C110,24 130,10 160,12 C180,13 195,8 200,6"
          fill="none"
          stroke="hsl(180 100% 55%)"
          strokeWidth="2"
        />
        <path
          d="M0,40 C30,42 50,20 80,22 C110,24 130,10 160,12 C180,13 195,8 200,6 L200,60 L0,60 Z"
          fill="hsl(180 100% 55% / 0.15)"
        />
      </svg>
    ),
  },
];

const FeatureCard = ({ f, i }: { f: typeof features[number]; i: number }) => {
  const { ref, visible } = useReveal();
  return (
    <div
      ref={ref}
      className={`group glass rounded-3xl p-7 hover:border-primary/30 hover:-translate-y-1 transition-all duration-500 ${visible ? "animate-fade-up" : "opacity-0"}`}
      style={{ animationDelay: `${i * 120}ms` }}
    >
      <div
        className="w-12 h-12 rounded-2xl grid place-items-center mb-5 transition-shadow group-hover:shadow-[0_0_30px_hsl(var(--glow-primary)/0.5)]"
        style={{ background: `hsl(${f.accent} / 0.15)`, color: `hsl(${f.accent})` }}
      >
        <f.icon className="w-5 h-5" />
      </div>
      <h3 className="font-display text-2xl font-semibold mb-2">{f.title}</h3>
      <p className="text-muted-foreground text-sm leading-relaxed mb-6">{f.desc}</p>
      <div className="rounded-2xl bg-muted/30 p-3 border border-border/50">{f.preview}</div>
    </div>
  );
};

export const CoreValue = () => {
  return (
    <section id="features" className="py-28 relative">
      <div className="container mx-auto px-6">
        <SectionHeader
          eyebrow="Core Values"
          title={<>From Tracking to <span className="text-gradient">Intelligence</span></>}
          subtitle="Three engines working together to turn raw health data into actionable foresight."
        />

        <div className="grid md:grid-cols-3 gap-6">
          {features.map((f, i) => (
            <FeatureCard key={f.title} f={f} i={i} />
          ))}
        </div>
      </div>
    </section>
  );
};
