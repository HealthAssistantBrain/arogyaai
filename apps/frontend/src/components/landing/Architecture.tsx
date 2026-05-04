import { Zap, Boxes, Radio, GitBranch } from "lucide-react";
import { SectionHeader } from "./CoreValue";

const points = [
  { icon: Zap, title: "Async Processing", desc: "Non-blocking pipelines. Zero waiting UIs." },
  { icon: Boxes, title: "Microservices", desc: "Decoupled inference, ingestion, and explanation services." },
  { icon: Radio, title: "Real-time + Background", desc: "Low-latency reads, heavy ML in background workers." },
  { icon: GitBranch, title: "Scalable ML Pipelines", desc: "Versioned models, reproducible training, online updates." },
];

export const Architecture = () => {
  return (
    <section className="py-28 relative">
      <div className="container mx-auto px-6">
        <SectionHeader
          eyebrow="Performance & Architecture"
          title={<>Engineered Like a <span className="text-gradient">Real AI System</span></>}
        />
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {points.map((p) => (
            <div key={p.title} className="glass rounded-2xl p-6 group hover:-translate-y-1 transition-transform">
              <div className="w-11 h-11 rounded-xl bg-gradient-primary/15 grid place-items-center mb-4 border border-primary/20 group-hover:glow-primary transition-shadow">
                <p.icon className="w-5 h-5 text-primary" />
              </div>
              <div className="font-display font-semibold mb-1.5">{p.title}</div>
              <p className="text-sm text-muted-foreground leading-relaxed">{p.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
