import { Lock, KeyRound, ShieldCheck, ServerOff } from "lucide-react";
import { SectionHeader } from "./CoreValue";

const items = [
  { icon: KeyRound, title: "JWT Authentication", desc: "Stateless, secure tokens with rotation. No session leakage." },
  { icon: ServerOff, title: "No Local Token Storage", desc: "Sensitive credentials never persisted in browser storage." },
  { icon: Lock, title: "End-to-End Protection", desc: "TLS in transit, encrypted at rest. Granular access scopes." },
  { icon: ShieldCheck, title: "Local-First Architecture", desc: "Your raw data stays where it belongs — yours." },
];

export const Trust = () => {
  return (
    <section className="py-28 relative">
      <div className="container mx-auto px-6">
        <SectionHeader
          eyebrow="Trust & Security"
          title={<>Built for <span className="text-gradient">Sensitive Health Data</span></>}
          subtitle="Designed from day one with privacy, integrity, and clinical-grade security in mind."
        />

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {items.map((it) => (
            <div key={it.title} className="glass rounded-2xl p-6 hover:border-accent/40 transition-colors">
              <div className="w-11 h-11 rounded-xl bg-accent/10 text-accent grid place-items-center mb-4">
                <it.icon className="w-5 h-5" />
              </div>
              <div className="font-display font-semibold mb-1.5">{it.title}</div>
              <p className="text-sm text-muted-foreground leading-relaxed">{it.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};
