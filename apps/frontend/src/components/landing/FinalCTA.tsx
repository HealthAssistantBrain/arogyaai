import { ArrowRight, LayoutDashboard } from "lucide-react";
import { Link } from "react-router-dom";

export const FinalCTA = () => {
  return (
    <section id="cta" className="py-32 relative overflow-hidden">
      {/* particles */}
      <div className="absolute inset-0 pointer-events-none">
        {Array.from({ length: 30 }).map((_, i) => (
          <span
            key={i}
            className="absolute rounded-full bg-primary/40 animate-float"
            style={{
              width: `${2 + (i % 4)}px`,
              height: `${2 + (i % 4)}px`,
              left: `${(i * 37) % 100}%`,
              top: `${(i * 53) % 100}%`,
              animationDelay: `${(i % 6) * 0.6}s`,
              animationDuration: `${5 + (i % 5)}s`,
              filter: "blur(0.5px)",
              boxShadow: "0 0 8px hsl(var(--glow-primary))",
            }}
          />
        ))}
      </div>
      <div className="absolute inset-0 bg-gradient-hero pointer-events-none" />

      <div className="container mx-auto px-6 relative">
        <div className="max-w-3xl mx-auto text-center glass-strong rounded-[2rem] p-12 md:p-16 glow-strong">
          <h2 className="font-display text-4xl md:text-6xl font-semibold tracking-tight">
            Start <span className="text-gradient">Understanding</span><br /> Your Health Today
          </h2>
          <p className="mt-5 text-muted-foreground text-lg">
            Predict. Explain. Prevent. The future of personal health intelligence is here.
          </p>
          <div className="mt-9 flex flex-col sm:flex-row gap-3 justify-center">
            <Link
              to="/dashboard"
              className="group inline-flex items-center justify-center gap-2 px-7 py-4 rounded-full bg-gradient-primary text-primary-foreground font-medium glow-primary hover:glow-strong transition-all"
            >
              Start Analysis
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>
            <Link
              to="/login"
              className="inline-flex items-center justify-center gap-2 px-7 py-4 rounded-full glass-strong font-medium hover:bg-card/80 transition-colors border border-secondary/40 text-secondary"
            >
              <LayoutDashboard className="w-4 h-4" />
              Login
            </Link>
          </div>
        </div>

        <footer className="mt-16 text-center text-xs text-muted-foreground">
          © {new Date().getFullYear()} ArogyaAI · Predictive Health Intelligence
        </footer>
      </div>
    </section>
  );
};
