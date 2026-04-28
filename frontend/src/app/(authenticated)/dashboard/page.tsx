"use client";

import { useEffect, useState } from "react";
import { Activity, Bot, FolderOpen, ShieldAlert, TrendingUp } from "lucide-react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "@/lib/api";
import type { DashboardStatsRecord } from "@/lib/types";
import { InsightCard, Panel, SectionDivider, Skeleton, StatCard } from "@/components/ui";

function chartStyle() {
  return {
    contentStyle: {
      background: "rgba(255,252,246,0.98)",
      border: "1px solid rgba(24,23,18,0.82)",
      borderRadius: 0,
      boxShadow: "0 18px 48px rgba(19,18,15,0.08)",
      color: "#12110e",
      fontFamily: '"IBM Plex Mono", monospace',
      fontSize: "12px",
      letterSpacing: "0.08em",
      textTransform: "uppercase" as const,
    },
  };
}

export default function DashboardPage() {
  const [stats, setStats] = useState<DashboardStatsRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const data = await api.getDashboardStats();
        setStats(data);
      } catch (err) {
        console.error("Failed to load dashboard stats", err);
        setError(err instanceof Error ? err.message : "Unable to load dashboard data");
      } finally {
        setLoading(false);
      }
    };
    loadStats();
  }, []);

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <div className="panel-card max-w-md p-10 text-center">
          <p className="panel-kicker text-red-500">Stability alert</p>
          <h2 className="section-title mt-4">Unable to load dashboard</h2>
          <p className="panel-subtle mt-4">{error}</p>
          <button 
            onClick={() => window.location.reload()} 
            className="btn-primary mt-8"
          >
            Retry connection
          </button>
        </div>
      </div>
    );
  }

  if (loading || !stats) {
    return (
      <div className="space-y-6">
        <Skeleton height="280px" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-4">
          {[1, 2, 3, 4].map((item) => (
            <Skeleton key={item} height="180px" />
          ))}
        </div>
        <Skeleton height="420px" />
      </div>
    );
  }

  const confidenceData = [
    { name: "High risk", value: stats?.high_confidence_count || 0, fill: "#efcfbf" },
    { name: "Review", value: stats?.medium_confidence_count || 0, fill: "#f3e37c" },
    { name: "Low", value: stats?.low_confidence_count || 0, fill: "#c5df7b" },
  ];
  const hasTrendData = (stats?.trend_data ?? []).some(
    (point) => point.detections > 0 || point.cases > 0
  );
  const hasConfidenceData = confidenceData.some((item) => item.value > 0);

  return (
    <div className="space-y-8">
      <section className="panel-card animate-in overflow-hidden px-6 py-8 md:px-10 md:py-12">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,1.2fr)_420px]">
          <div>
            <p className="panel-kicker">Dashboard / Control room</p>
            <h1 className="section-title mt-5 max-w-4xl text-[clamp(3.25rem,9vw,7.5rem)]">
              Protect your digital assets
            </h1>
            <p className="panel-subtle mt-6 max-w-2xl text-base">
              Gemini rationale, takedown drafting, and review signals stay visible
              without blocking the core workflow. The dashboard surfaces where the
              platform is confident, where it fell back safely, and which sources
              keep appearing at the top of the queue.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-px border border-[var(--color-line)] bg-[var(--color-line)] sm:grid-cols-2">
            <StatCard
              title="Protected assets"
              value={stats?.total_assets || 0}
              icon={<FolderOpen size={18} />}
              trend="Registry coverage"
              tone="neutral"
            />
            <StatCard
              title="Open cases"
              value={stats?.open_cases || 0}
              icon={<ShieldAlert size={18} />}
              trend="Analyst queue"
              tone="warning"
            />
            <StatCard
              title="High confidence"
              value={stats?.high_confidence_count || 0}
              icon={<TrendingUp size={18} />}
              trend="Immediate review"
              tone="success"
            />
            <StatCard
              title="AI ready"
              value={
                stats?.gemini_overview?.find((item) => item.title === "Gemini ready")
                  ?.value || 0
              }
              icon={<Bot size={18} />}
              trend="Rationale + draft"
              tone="info"
            />
          </div>

        </div>
      </section>

      <section className="animate-in" style={{ animationDelay: "0.05s" }}>
        <SectionDivider label="Global AI insights" />
        <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-4">
          {(stats.gemini_overview ?? []).length > 0 ? (
            stats.gemini_overview?.map((item) => (
              <InsightCard
                key={item.title}
                title={item.title}
                value={item.value}
                trend={item.trend}
                subtitle={item.subtitle}
                tone={
                  item.tone === "success" ||
                  item.tone === "warning" ||
                  item.tone === "info"
                    ? item.tone
                    : "neutral"
                }
              />
            ))
          ) : (
            <div className="panel-card col-span-full py-8 text-center">
              <p className="panel-subtle italic">AI insights summary pending for active cases</p>
            </div>
          )}
        </div>
      </section>

      <section className="animate-in" style={{ animationDelay: "0.1s" }}>
        <SectionDivider label="Top flagged sources" />
        <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-4 md:grid-cols-2">
          {(stats.top_flagged_sources ?? []).length > 0 ? (
            stats.top_flagged_sources?.map((item) => (
              <InsightCard
                key={item.title}
                title={item.title}
                value={item.value}
                trend={item.trend}
                subtitle={item.subtitle}
                tone={
                  item.tone === "success" ||
                  item.tone === "warning" ||
                  item.tone === "risk"
                    ? item.tone
                    : "neutral"
                }
              />
            ))
          ) : (
            <div className="panel-card col-span-full py-8 text-center">
              <p className="panel-subtle italic">Source distribution metadata unavailable</p>
            </div>
          )}
        </div>
      </section>


      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,0.8fr)]">
        <Panel
          kicker="Detection trend"
          title="Signals over the last seven days"
          className="animate-in p-6"
        >
          {hasTrendData ? (
            <ResponsiveContainer width="100%" height={340}>
              <AreaChart data={stats?.trend_data ?? []}>
                <defs>
                  <linearGradient id="detectionsFill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#7cd5e9" stopOpacity={0.65} />
                    <stop offset="100%" stopColor="#7cd5e9" stopOpacity={0.08} />
                  </linearGradient>
                  <linearGradient id="casesFill" x1="0" x2="0" y1="0" y2="1">
                    <stop offset="0%" stopColor="#c5df7b" stopOpacity={0.65} />
                    <stop offset="100%" stopColor="#c5df7b" stopOpacity={0.08} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(24,23,18,0.18)" />
                <XAxis
                  dataKey="date"
                  stroke="rgba(18,17,14,0.55)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  stroke="rgba(18,17,14,0.55)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip {...chartStyle()} />
                <Area
                  type="monotone"
                  dataKey="detections"
                  stroke="#12110e"
                  strokeWidth={2}
                  fill="url(#detectionsFill)"
                />
                <Area
                  type="monotone"
                  dataKey="cases"
                  stroke="#6a8717"
                  strokeWidth={2}
                  fill="url(#casesFill)"
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[340px] items-center justify-center border border-[var(--color-line)] bg-[rgba(255,255,255,0.45)] px-6 text-center">
              <p className="panel-subtle max-w-md">
                Signal history will appear here once detections or cases start flowing in from scans.
              </p>
            </div>
          )}
        </Panel>

        <Panel
          kicker="Confidence distribution"
          title="Threat mix"
          className="animate-in p-6"
        >
          {hasConfidenceData ? (
            <ResponsiveContainer width="100%" height={340}>
              <BarChart data={confidenceData} layout="vertical" margin={{ left: 10, right: 10 }}>
                <CartesianGrid stroke="rgba(24,23,18,0.18)" />
                <XAxis
                  type="number"
                  stroke="rgba(18,17,14,0.55)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  dataKey="name"
                  type="category"
                  width={90}
                  stroke="rgba(18,17,14,0.55)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip {...chartStyle()} />
                <Bar dataKey="value" radius={0} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-[340px] items-center justify-center border border-[var(--color-line)] bg-[rgba(255,255,255,0.45)] px-6 text-center">
              <p className="panel-subtle max-w-md">
                Confidence bands will populate after the first detections are scored.
              </p>
            </div>
          )}

          <div className="mt-6 grid grid-cols-2 gap-px border border-[var(--color-line)] bg-[var(--color-line)]">
            <StatCard
              title="Detections"
              value={stats?.total_scans || 0}
              trend="Signals processed"
              icon={<Activity size={18} />}
              tone="neutral"
            />
            <StatCard
              title="Cases"
              value={stats?.total_detections || 0}
              trend="Potential infringements"
              icon={<ShieldAlert size={18} />}
              tone="info"
            />
          </div>
        </Panel>
      </div>
    </div>
  );
}
