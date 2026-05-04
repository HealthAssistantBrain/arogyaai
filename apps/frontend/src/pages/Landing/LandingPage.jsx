import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';

import { Navbar } from "@/components/landing/Navbar";
import { Hero } from "@/components/landing/Hero";
import { CoreValue } from "@/components/landing/CoreValue";
import { HowItWorks } from "@/components/landing/HowItWorks";
import { DashboardPreview } from "@/components/landing/DashboardPreview";
import { AIExplain } from "@/components/landing/AIExplain";
import { Trust } from "@/components/landing/Trust";
import { Architecture } from "@/components/landing/Architecture";
import { FeaturesGrid } from "@/components/landing/FeaturesGrid";
import { Research } from "@/components/landing/Research";
import { FinalCTA } from "@/components/landing/FinalCTA";

const LandingPage = () => {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  // STEP 7 — AUTH GUARD
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  return (
    <main className="min-h-screen relative overflow-x-hidden bg-background text-foreground">
      <Navbar />
      <Hero />
      <CoreValue />
      <HowItWorks />
      <DashboardPreview />
      <AIExplain />
      <Trust />
      <Architecture />
      <FeaturesGrid />
      <Research />
      <FinalCTA />
    </main>
  );
};

export default LandingPage;
