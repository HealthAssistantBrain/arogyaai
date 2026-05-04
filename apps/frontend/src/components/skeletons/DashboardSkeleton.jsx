import React from 'react';
import { motion } from 'framer-motion';

const DashboardSkeleton = () => {
  return (
    <motion.div
      key="skeleton"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      className="flex-1 flex flex-col min-w-0"
    >
      <div className="p-8 space-y-8 max-w-7xl mx-auto w-full">
        {/* Header */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-2">
          <div>
            <div className="h-8 w-40 bg-slate-200 dark:bg-card rounded animate-pulse"></div>
          </div>
          <div className="h-10 w-32 bg-slate-200 dark:bg-card rounded-xl animate-pulse"></div>
        </div>

        {/* Section 1: Hero Stats Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="lg:col-span-1 bg-white dark:bg-background p-8 rounded-xl shadow-sm border border-slate-100 dark:border-stroke flex flex-col items-center justify-center relative overflow-hidden h-[340px]">
            <div className="h-4 w-32 bg-slate-100 dark:bg-card rounded animate-pulse mb-8"></div>
            <div className="size-48 bg-slate-100 dark:bg-card rounded-full animate-pulse"></div>
            <div className="h-4 w-48 bg-slate-100 dark:bg-card rounded animate-pulse mt-8"></div>
          </div>
          <div className="lg:col-span-1 bg-slate-100 dark:bg-card p-8 rounded-xl shadow-sm border border-slate-200 dark:border-stroke flex flex-col items-center justify-center relative overflow-hidden h-[340px] animate-pulse">
          </div>
        </div>

        {/* Heart Rate Card */}
        <div className="h-48 w-full bg-white dark:bg-background rounded-xl border border-slate-100 dark:border-stroke animate-pulse"></div>

        {/* Section 2: AI Prediction */}
        <div className="relative overflow-hidden rounded-xl p-8 bg-slate-200 dark:bg-card shadow-xl border border-slate-100 dark:border-stroke h-[300px] animate-pulse"></div>

        {/* Vitals Cards */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-28 bg-white dark:bg-background rounded-xl border border-slate-100 dark:border-stroke animate-pulse"></div>
          ))}
        </div>

        {/* Section 3: Secondary Stats Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="bg-white dark:bg-background p-8 rounded-xl shadow-sm border border-slate-100 dark:border-stroke h-[280px] animate-pulse"></div>
          ))}
        </div>

        {/* Section 4: Critical Alerts & Recommendations */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pb-12">
          <div className="bg-white dark:bg-background p-8 rounded-xl shadow-sm border-l-4 border-slate-200 dark:border-stroke h-[300px] animate-pulse"></div>
          <div className="bg-white dark:bg-background p-8 rounded-xl shadow-sm border border-slate-100 dark:border-stroke h-[300px] animate-pulse"></div>
        </div>
      </div>
    </motion.div>
  );
};

export default DashboardSkeleton;

