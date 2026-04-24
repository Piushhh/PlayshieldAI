"use client";

import clsx from "clsx";
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  Info,
  Sparkles,
} from "lucide-react";
import React from "react";

type Tone = "neutral" | "info" | "success" | "warning" | "risk";

function toneClasses(tone: Tone) {
  switch (tone) {
    case "info":
      return "border-[var(--color-info-border)] bg-[var(--color-info-bg)] text-[var(--color-ink)]";
    case "success":
      return "border-[var(--color-success-border)] bg-[var(--color-success-bg)] text-[var(--color-ink)]";
    case "warning":
      return "border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] text-[var(--color-ink)]";
    case "risk":
      return "border-[var(--color-risk-border)] bg-[var(--color-risk-bg)] text-[var(--color-ink)]";
    default:
      return "border-[var(--color-line)] bg-[var(--color-panel)] text-[var(--color-ink)]";
  }
}

function scoreTone(score: number): Tone {
  if (score >= 0.85) return "risk";
  if (score >= 0.6) return "warning";
  return "success";
}

export function ScoreBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  return (
    <span className={clsx("score-badge", toneClasses(scoreTone(score)))}>
      {pct}
      <small>% confidence</small>
    </span>
  );
}

export function StatusPill({ status }: { status: string }) {
  const labelMap: Record<string, string> = {
    new: "New",
    review: "Reviewed",
    actioned: "Actioned",
    rejected: "Rejected",
  };
  const toneMap: Record<string, Tone> = {
    new: "info",
    review: "success",
    actioned: "neutral",
    rejected: "warning",
  };

  return (
    <span className={clsx("status-pill", toneClasses(toneMap[status] || "neutral"))}>
      {labelMap[status] || status}
    </span>
  );
}

export function PriorityBadge({ priority }: { priority: string }) {
  const toneMap: Record<string, Tone> = {
    critical: "risk",
    high: "warning",
    medium: "info",
    low: "success",
  };
  return (
    <span className={clsx("status-pill", toneClasses(toneMap[priority] || "neutral"))}>
      {priority}
    </span>
  );
}

export function Skeleton({
  width = "100%",
  height = "20px",
  className,
}: {
  width?: string;
  height?: string;
  className?: string;
}) {
  return <div className={clsx("skeleton", className)} style={{ width, height }} />;
}

export function StatCard({
  title,
  value,
  icon,
  trend,
  tone = "neutral",
}: {
  title: string;
  value: string | number;
  icon?: React.ReactNode;
  trend?: string;
  tone?: Tone;
}) {
  return (
    <div className={clsx("metric-tile", toneClasses(tone))}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="panel-kicker">{title}</p>
          <p className="metric-value">{value}</p>
          {trend ? <p className="metric-trend">{trend}</p> : null}
        </div>
        {icon ? <div className="metric-icon">{icon}</div> : null}
      </div>
    </div>
  );
}

export function InsightCard({
  title,
  value,
  trend,
  subtitle,
  tone = "neutral",
}: {
  title: string;
  value: string | number;
  trend: string;
  subtitle: string;
  tone?: Tone;
}) {
  return (
    <div className={clsx("panel-card", toneClasses(tone))}>
      <p className="panel-kicker">{subtitle}</p>
      <div className="mt-5 flex items-end justify-between gap-4">
        <div>
          <h3 className="section-title text-xl">{title}</h3>
          <p className="panel-subtle mt-2">{trend}</p>
        </div>
        <div className="accent-box">
          <span>{String(value).padStart(2, "0")}</span>
        </div>
      </div>
    </div>
  );
}

export function Panel({
  kicker,
  title,
  children,
  className,
  actions,
}: {
  kicker?: string;
  title?: string;
  children: React.ReactNode;
  className?: string;
  actions?: React.ReactNode;
}) {
  return (
    <section className={clsx("panel-card", className)}>
      {(kicker || title || actions) && (
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            {kicker ? <p className="panel-kicker">{kicker}</p> : null}
            {title ? <h2 className="section-title mt-2">{title}</h2> : null}
          </div>
          {actions}
        </div>
      )}
      {children}
    </section>
  );
}

export function Callout({
  title,
  description,
  tone = "info",
  badge,
  icon,
  className,
}: {
  title: string;
  description: React.ReactNode;
  tone?: Tone;
  badge?: string;
  icon?: React.ReactNode;
  className?: string;
}) {
  const defaultIcon =
    tone === "warning" || tone === "risk" ? <AlertTriangle size={18} /> : <Info size={18} />;

  return (
    <div className={clsx("callout-card", toneClasses(tone), className)}>
      <div className="flex items-start gap-4">
        <div className="callout-icon">{icon || defaultIcon}</div>
        <div className="min-w-0 flex-1">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            {badge ? <span className="micro-badge">{badge}</span> : null}
            <h3 className="text-base font-semibold uppercase tracking-[0.18em]">{title}</h3>
          </div>
          <div className="panel-copy">{description}</div>
        </div>
      </div>
    </div>
  );
}

export function GeminiCallout({
  title,
  description,
  badge = "Gemini-powered rationale",
  className,
}: {
  title: string;
  description: React.ReactNode;
  badge?: string;
  className?: string;
}) {
  return (
    <Callout
      title={title}
      description={description}
      badge={badge}
      tone="info"
      icon={<Bot size={18} />}
      className={className}
    />
  );
}

export function SectionDivider({ label }: { label: string }) {
  return (
    <div className="section-divider">
      <span>{label}</span>
    </div>
  );
}

export function StickyActionBar({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={clsx("sticky-action-bar", className)}>{children}</div>;
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="panel-card py-12 text-center">
      <div className="mx-auto mb-5 flex h-12 w-12 items-center justify-center rounded-full border border-[var(--color-line)] bg-[var(--color-panel-muted)]">
        <Sparkles size={18} />
      </div>
      <h3 className="section-title text-lg">{title}</h3>
      <p className="panel-subtle mx-auto mt-3 max-w-xl">{description}</p>
      {action ? <div className="mt-6 flex justify-center">{action}</div> : null}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <Callout
      title="Something needs attention"
      description={
        <div className="space-y-4">
          <p>{message}</p>
          {onRetry ? (
            <button onClick={onRetry} className="btn-secondary">
              Try again
            </button>
          ) : null}
        </div>
      }
      tone="warning"
      badge="AI services delayed"
      icon={<AlertTriangle size={18} />}
    />
  );
}

export function DraftReviewedBadge() {
  return (
    <span className={clsx("status-pill", toneClasses("success"))}>
      <CheckCircle2 size={14} />
      Reviewed
    </span>
  );
}

export function Modal({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}) {
  if (!open) return null;
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(event) => event.stopPropagation()}>
        <div className="mb-6 flex items-center justify-between gap-4">
          <div>
            <p className="panel-kicker">Action modal</p>
            <h2 className="section-title mt-2">{title}</h2>
          </div>
          <button onClick={onClose} className="btn-secondary px-3 py-2">
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
