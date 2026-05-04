import { Watch, ScanLine, Brain, Sparkles, LineChart, Clock } from "lucide-react";
import { SectionHeader } from "./CoreValue";

const features = [
  { icon: Watch, title: "Wearable Sync", desc: "Google Fit & Apple Health ready" },
  { icon: ScanLine, title: "Lab Report OCR", desc: "Upload PDF / image, auto-extract values" },
  { icon: Brain, title: "AI Predictions", desc: "Diabetes, cardio risk and more" },
  { icon: Sparkles, title: "Preventive Insights", desc: "Personalized, evidence-based actions" },
  { icon: LineChart, title: "Health Score", desc: "One number, full-stack signals" },
  { icon: Clock, title: "Timeline View", desc: "Long-term trends, future-ready" },
];

const useCases = [
  "Early disease detection",
  "Fitness optimization",
  "Lifestyle improvement",
  "Preventive healthcare",
];

export const FeaturesGrid = () => {
  return (
    <section className="py-28 relative">
      <div className="container mx-auto px-6">
        <SectionHeader
          eyebrow="Capabilities"
          title={<>A complete <span className="text-gradient">health intelligence</span> stack</>}
        />

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-14">
          {features.map((f) => (
            <div key={f.title} className="glass rounded-2xl p-5 flex items-start gap-4 hover:border-primary/30 transition-colors">
              <div className="w-10 h-10 rounded-xl bg-gradient-primary/15 border border-primary/20 grid place-items-center shrink-0">
                <f.icon className="w-4.5 h-4.5 text-primary" />
              </div>
              <div>
                <div className="font-display font-semibold">{f.title}</div>
                <p className="text-sm text-muted-foreground">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="glass-strong rounded-3xl p-8">
          <div className="text-xs text-primary mb-4">USE CASES</div>
          <div className="flex flex-wrap gap-3">
            {useCases.map((u) => (
              <div key={u} className="px-4 py-2 rounded-full glass text-sm hover:border-primary/40 transition-colors">
                {u}
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
