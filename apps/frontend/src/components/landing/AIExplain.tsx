import { Sparkles, FileText } from "lucide-react";
import { SectionHeader } from "./CoreValue";

const factors = [
  { name: "Elevated glucose", impact: 38, dir: "up" },
  { name: "Reduced sleep quality", impact: 24, dir: "up" },
  { name: "Low daily activity", impact: 16, dir: "up" },
  { name: "Healthy HRV", impact: 12, dir: "down" },
  { name: "BMI within range", impact: 10, dir: "down" },
];

export const AIExplain = () => {
  return (
    <section className="py-28 relative">
      <div className="container mx-auto px-6">
        <SectionHeader
          eyebrow="Explainable AI"
          title={<>Not Just Results — <span className="text-gradient">Real Understanding</span></>}
          subtitle="Every prediction is decomposed into its underlying contributors so clinicians and users can trust it."
        />

        <div className="grid lg:grid-cols-5 gap-6 items-stretch">
          {/* SHAP visualization */}
          <div className="glass-strong rounded-3xl p-6 lg:col-span-3">
            <div className="flex items-center justify-between mb-6">
              <div>
                <div className="text-xs text-muted-foreground">Diabetes Risk Score</div>
                <div className="font-display text-3xl font-semibold text-warning">62%</div>
              </div>
              <div className="text-xs text-muted-foreground">SHAP Contribution Analysis</div>
            </div>

            <div className="space-y-3">
              {factors.map((f) => (
                <div key={f.name} className="flex items-center gap-4">
                  <div className="w-44 text-sm text-muted-foreground">{f.name}</div>
                  <div className="flex-1 flex items-center">
                    <div className="flex-1 flex justify-end">
                      {f.dir === "down" && (
                        <div
                          className="h-6 rounded-l-md"
                          style={{
                            width: `${f.impact * 2}%`,
                            background: "linear-gradient(90deg, hsl(142 76% 50% / 0.2), hsl(142 76% 50%))",
                          }}
                        />
                      )}
                    </div>
                    <div className="w-px h-8 bg-border" />
                    <div className="flex-1">
                      {f.dir === "up" && (
                        <div
                          className="h-6 rounded-r-md"
                          style={{
                            width: `${f.impact * 2}%`,
                            background: "linear-gradient(90deg, hsl(0 90% 60%), hsl(0 90% 60% / 0.2))",
                          }}
                        />
                      )}
                    </div>
                  </div>
                  <div className="w-10 text-right text-sm tabular-nums font-mono">
                    {f.dir === "up" ? "+" : "−"}{f.impact}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-destructive" /> Increases risk</span>
              <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-sm bg-success" /> Decreases risk</span>
            </div>
          </div>

          {/* Natural language */}
          <div className="lg:col-span-2 space-y-4">
            <div className="glass rounded-3xl p-6">
              <div className="flex items-center gap-2 text-primary text-xs mb-3">
                <Sparkles className="w-4 h-4" /> AI Explanation
              </div>
              <p className="leading-relaxed">
                Your <span className="text-warning font-medium">diabetes risk increased</span> primarily due to
                <span className="text-foreground"> elevated glucose levels</span> and
                <span className="text-foreground"> reduced sleep quality</span> over the past 14 days.
                Healthy HRV and BMI are mitigating factors.
              </p>
            </div>
            <div className="glass rounded-3xl p-6">
              <div className="flex items-center gap-2 text-accent text-xs mb-3">
                <FileText className="w-4 h-4" /> Evidence
              </div>
              <ul className="text-sm text-muted-foreground space-y-2">
                <li>• ADA 2024 guidelines on prediabetes screening</li>
                <li>• 14-day glucose trend exceeds 120 mg/dL avg</li>
                <li>• Sleep efficiency dropped 12% week-over-week</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
