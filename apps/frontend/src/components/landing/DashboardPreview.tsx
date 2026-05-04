import { Heart, Moon, Footprints, Droplet, Activity, TrendingUp, TrendingDown } from "lucide-react";
import { SectionHeader } from "./CoreValue";

const metrics = [
  { icon: Heart, label: "Heart Rate", value: "72", unit: "bpm", trend: "down", risk: "normal", color: "hsl(0 90% 65%)" },
  { icon: Footprints, label: "Steps", value: "8,432", unit: "today", trend: "up", risk: "normal", color: "hsl(180 100% 55%)" },
  { icon: Moon, label: "Sleep", value: "7h 12m", unit: "avg", trend: "up", risk: "normal", color: "hsl(265 85% 70%)" },
  { icon: Droplet, label: "Glucose", value: "142", unit: "mg/dL", trend: "up", risk: "high", color: "hsl(38 95% 60%)" },
  { icon: Activity, label: "Blood Pressure", value: "128/84", unit: "mmHg", trend: "down", risk: "normal", color: "hsl(200 100% 60%)" },
  { icon: Heart, label: "HRV", value: "58", unit: "ms", trend: "up", risk: "normal", color: "hsl(142 76% 50%)" },
];

const Spark = ({ color, abnormal }: { color: string; abnormal?: boolean }) => (
  <svg viewBox="0 0 100 30" className="w-full h-10">
    <path
      d={abnormal ? "M0,20 L15,18 L30,22 L45,14 L60,16 L75,8 L90,4 L100,2" : "M0,18 L15,20 L30,15 L45,17 L60,12 L75,14 L90,10 L100,11"}
      fill="none"
      stroke={color}
      strokeWidth="1.8"
      strokeLinecap="round"
    />
  </svg>
);

export const DashboardPreview = () => {
  return (
    <section id="dashboard" className="py-28 relative">
      <div className="container mx-auto px-6">
        <SectionHeader
          eyebrow="Live Intelligence"
          title={<>Your Health, <span className="text-gradient">Visualized</span> in Real-Time</>}
          subtitle="Glanceable scores, live trends, and abnormal-metric detection — all in one calm interface."
        />

        <div className="glass-strong rounded-3xl p-6 md:p-8 relative overflow-hidden">
          <div className="absolute -top-20 -right-20 w-72 h-72 bg-primary/20 rounded-full blur-3xl pointer-events-none" />
          <div className="absolute -bottom-20 -left-20 w-72 h-72 bg-secondary/20 rounded-full blur-3xl pointer-events-none" />

          <div className="grid lg:grid-cols-3 gap-6 relative">
            {/* Score card */}
            <div className="glass rounded-2xl p-6 lg:col-span-1">
              <div className="text-xs text-muted-foreground">Overall Health Score</div>
              <div className="mt-2 flex items-end gap-2">
                <span className="font-display text-6xl font-semibold text-gradient">87</span>
                <span className="pb-2 text-muted-foreground text-sm">/ 100</span>
              </div>
              <div className="mt-4 h-2 rounded-full bg-muted overflow-hidden">
                <div className="h-full bg-gradient-primary" style={{ width: "87%" }} />
              </div>
              <div className="mt-6 grid grid-cols-3 gap-2 text-center text-xs">
                <div className="p-2 rounded-lg bg-success/10 text-success">Cardio<br/><span className="font-semibold">Normal</span></div>
                <div className="p-2 rounded-lg bg-warning/10 text-warning">Glucose<br/><span className="font-semibold">High</span></div>
                <div className="p-2 rounded-lg bg-success/10 text-success">Sleep<br/><span className="font-semibold">Normal</span></div>
              </div>
            </div>

            {/* Metric grid */}
            <div className="lg:col-span-2 grid sm:grid-cols-2 gap-3">
              {metrics.map((m) => {
                const abnormal = m.risk === "high";
                return (
                  <div
                    key={m.label}
                    className={`group rounded-2xl p-4 border transition-all duration-300 hover:-translate-y-0.5 ${
                      abnormal
                        ? "bg-destructive/5 border-destructive/40 hover:shadow-[0_0_30px_hsl(var(--destructive)/0.3)]"
                        : "glass border-border hover:border-primary/30"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <m.icon className="w-3.5 h-3.5" style={{ color: m.color }} />
                        {m.label}
                      </div>
                      {m.trend === "up" ? (
                        <TrendingUp className={`w-3.5 h-3.5 ${abnormal ? "text-destructive" : "text-success"}`} />
                      ) : (
                        <TrendingDown className="w-3.5 h-3.5 text-muted-foreground" />
                      )}
                    </div>
                    <div className="flex items-baseline gap-1">
                      <span className={`font-display text-2xl font-semibold ${abnormal ? "text-destructive" : ""}`}>
                        {m.value}
                      </span>
                      <span className="text-xs text-muted-foreground">{m.unit}</span>
                    </div>
                    <Spark color={m.color} abnormal={abnormal} />
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
