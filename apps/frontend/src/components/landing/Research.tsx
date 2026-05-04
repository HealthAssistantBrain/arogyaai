import { FlaskConical, BookOpen, Brain, Globe2 } from "lucide-react";
import { SectionHeader } from "./CoreValue";

const pillars = [
  { icon: Brain, title: "Explainable AI (SHAP)", desc: "Decompose every prediction into transparent contributing signals." },
  { icon: BookOpen, title: "Retrieval-Augmented Generation", desc: "Insights grounded in curated medical literature." },
  { icon: FlaskConical, title: "Medical Knowledge Integration", desc: "Clinical ontologies and guidelines woven into the model layer." },
  { icon: Globe2, title: "Real-World Impact", desc: "Designed to scale across devices, demographics and care settings." },
];

export const Research = () => {
  return (
    <section id="research" className="py-28 relative">
      <div className="container mx-auto px-6">
        <SectionHeader
          eyebrow="Research & Innovation"
          title={<>Built as a <span className="text-gradient">Health Intelligence</span> Research Platform</>}
        />
        <div className="grid md:grid-cols-2 gap-5">
          {pillars.map((p) => (
            <div key={p.title} className="glass rounded-3xl p-7 flex gap-5 hover:border-secondary/30 transition-colors">
              <div className="w-12 h-12 shrink-0 rounded-2xl bg-secondary/15 border border-secondary/30 grid place-items-center">
                <p.icon className="w-5 h-5 text-secondary" />
              </div>
              <div>
                <h3 className="font-display text-xl font-semibold mb-1.5">{p.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{p.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
