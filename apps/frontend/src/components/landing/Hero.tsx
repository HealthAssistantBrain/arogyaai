import { ArrowRight, PlayCircle, Heart, Moon, Footprints, Droplet, Sparkles, TrendingUp, TrendingDown } from "lucide-react";

const Sparkline = ({ color = "hsl(var(--primary))" }: { color?: string }) => (
  <svg viewBox="0 0 100 30" className="w-full h-8">
    <defs>
      <linearGradient id={`g-${color}`} x1="0" x2="0" y1="0" y2="1">
        <stop offset="0%" stopColor={color} stopOpacity="0.4" />
        <stop offset="100%" stopColor={color} stopOpacity="0" />
      </linearGradient>
    </defs>
    <path
      d="M0,22 L12,18 L24,20 L36,12 L48,15 L60,8 L72,11 L84,5 L100,9"
      fill="none"
      stroke={color}
      strokeWidth="1.5"
      className="animate-draw"
    />
    <path
      d="M0,22 L12,18 L24,20 L36,12 L48,15 L60,8 L72,11 L84,5 L100,9 L100,30 L0,30 Z"
      fill={`url(#g-${color})`}
    />
  </svg>
);

const MetricCard = ({
  icon: Icon,
  label,
  value,
  unit,
  trend,
  color,
  delay = 0,
}: {
  icon: any;
  label: string;
  value: string;
  unit: string;
  trend: "up" | "down";
  color: string;
  delay?: number;
}) => (
  <div
    className="glass rounded-2xl p-4 hover:scale-[1.03] transition-transform duration-500 animate-fade-up"
    style={{ animationDelay: `${delay}ms` }}
  >
    <div className="flex items-center justify-between mb-2">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Icon className="w-3.5 h-3.5" style={{ color }} />
        {label}
      </div>
      {trend === "up" ? (
        <TrendingUp className="w-3.5 h-3.5 text-success" />
      ) : (
        <TrendingDown className="w-3.5 h-3.5 text-warning" />
      )}
    </div>
    <div className="flex items-baseline gap-1">
      <span className="font-display text-2xl font-semibold">{value}</span>
      <span className="text-xs text-muted-foreground">{unit}</span>
    </div>
    <div className="mt-1 -mx-1">
      <Sparkline color={color} />
    </div>
  </div>
);

export const Hero = () => {
  return (
    <section id="top" className="relative pt-32 pb-24 overflow-hidden">
      <div className="absolute inset-0 grid-bg pointer-events-none" />
      <div className="absolute inset-0 bg-gradient-hero pointer-events-none" />

      <div className="container mx-auto px-6 relative">
        <div className="grid lg:grid-cols-2 gap-12 items-center">
          {/* Left: copy */}
          <div className="max-w-xl">
            <div className="inline-flex items-center gap-2 glass rounded-full px-3 py-1.5 text-xs text-muted-foreground mb-6 animate-fade-in">
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
              Predictive Health Intelligence Platform
            </div>
            <h1 className="font-display text-5xl md:text-6xl lg:text-7xl font-semibold leading-[1.05] tracking-tight animate-fade-up">
              Predict Your <br />
              Health <span className="text-gradient">Before</span> <br />
              It Fails.
            </h1>
            <p
              className="mt-6 text-lg text-muted-foreground leading-relaxed animate-fade-up"
              style={{ animationDelay: "120ms" }}
            >
              ArogyaAI transforms wearable data and medical reports into
              real-time disease risk predictions with explainable AI insights.
            </p>
            <div
              className="mt-10 flex items-center gap-6 text-xs text-muted-foreground animate-fade-up"
              style={{ animationDelay: "360ms" }}
            >
              <div>
                <div className="font-display text-xl text-foreground">98.2%</div>
                Model accuracy
              </div>
              <div className="w-px h-8 bg-border" />
              <div>
                <div className="font-display text-xl text-foreground">&lt;200ms</div>
                Inference latency
              </div>
              <div className="w-px h-8 bg-border" />
              <div>
                <div className="font-display text-xl text-foreground">SHAP</div>
                Explainable AI
              </div>
            </div>
          </div>

          {/* Right: dashboard preview */}
          <div className="relative animate-fade-in" style={{ animationDelay: "200ms" }}>
            <div className="absolute -inset-10 bg-gradient-primary opacity-20 blur-3xl rounded-full pointer-events-none" />

            <div className="relative glass-strong rounded-3xl p-5 glow-primary">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-xs text-muted-foreground">Health Score</div>
                  <div className="font-display text-3xl font-semibold">
                    87<span className="text-base text-muted-foreground">/100</span>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs text-muted-foreground">Live</div>
                  <div className="flex items-center gap-1.5 text-xs text-success">
                    <span className="w-1.5 h-1.5 rounded-full bg-success animate-pulse" />
                    Synced
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <MetricCard icon={Heart} label="Heart Rate" value="72" unit="bpm" trend="down" color="hsl(0 90% 65%)" delay={0} />
                <MetricCard icon={Footprints} label="Steps" value="8.4k" unit="" trend="up" color="hsl(180 100% 55%)" delay={100} />
                <MetricCard icon={Moon} label="Sleep" value="7.2" unit="hrs" trend="up" color="hsl(265 85% 70%)" delay={200} />
                <MetricCard icon={Droplet} label="Glucose" value="118" unit="mg/dL" trend="down" color="hsl(38 95% 60%)" delay={300} />
              </div>

              {/* AI insight panel floating */}
              <div className="absolute -bottom-6 -left-6 right-6 sm:-left-10 sm:right-auto sm:w-72 glass-strong rounded-2xl p-4 animate-float border border-primary/30">
                <div className="flex items-center gap-2 text-xs text-primary mb-2">
                  <Sparkles className="w-3.5 h-3.5" />
                  AI Insight
                </div>
                <div className="text-sm leading-relaxed">
                  <span className="text-warning font-medium">Mild risk</span> of pre-diabetic trend detected.
                </div>
                <div className="mt-3 space-y-1.5">
                  {[
                    { label: "Glucose level", val: 72 },
                    { label: "Sleep quality", val: 48 },
                    { label: "Activity index", val: 25 },
                  ].map((f) => (
                    <div key={f.label} className="flex items-center gap-2 text-[11px]">
                      <span className="w-20 text-muted-foreground">{f.label}</span>
                      <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full bg-gradient-primary"
                          style={{ width: `${f.val}%` }}
                        />
                      </div>
                      <span className="text-muted-foreground tabular-nums">{f.val}%</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
