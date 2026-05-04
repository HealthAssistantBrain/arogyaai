import { Upload, Cpu, Activity, Sparkles, MessageSquare } from "lucide-react";
import { SectionHeader } from "./CoreValue";

const steps = [
  { icon: Upload, title: "Connect / Upload", desc: "Sync wearables or upload lab reports (PDF, image)." },
  { icon: Cpu, title: "AI Pipeline", desc: "Async ingestion, normalization & feature engineering." },
  { icon: Activity, title: "ML Prediction", desc: "Risk models score diabetes, cardio & more." },
  { icon: Sparkles, title: "SHAP Explains", desc: "Per-feature contribution to your risk score." },
  { icon: MessageSquare, title: "AI Insights", desc: "Personalized, RAG-grounded recommendations." },
];

export const HowItWorks = () => {
  return (
    <section id="how" className="py-28 relative">
      <div className="container mx-auto px-6">
        <SectionHeader
          eyebrow="System Flow"
          title={<>How <span className="text-gradient">ArogyaAI</span> Works</>}
          subtitle="A real intelligence pipeline — from raw signals to evidence-backed insight."
        />

        <div className="relative">
          <div className="hidden lg:block absolute top-12 left-0 right-0 h-px bg-gradient-to-r from-transparent via-primary/40 to-transparent" />
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-6">
            {steps.map((s, i) => (
              <div key={s.title} className="relative">
                <div className="glass rounded-2xl p-5 h-full hover:border-primary/40 transition-colors">
                  <div className="relative w-12 h-12 rounded-xl bg-gradient-primary/20 grid place-items-center mb-4 border border-primary/30">
                    <s.icon className="w-5 h-5 text-primary" />
                    <span className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-gradient-primary text-[11px] font-semibold text-primary-foreground grid place-items-center">
                      {i + 1}
                    </span>
                  </div>
                  <div className="font-display font-semibold">{s.title}</div>
                  <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">{s.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
