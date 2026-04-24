"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ExternalLink, Filter } from "lucide-react";
import { api } from "@/lib/api";
import type { CaseRecord } from "@/lib/types";
import {
  EmptyState,
  GeminiCallout,
  PriorityBadge,
  ScoreBadge,
  SectionDivider,
  Skeleton,
  StatusPill,
} from "@/components/ui";

export default function CasesPage() {
  const [cases, setCases] = useState<CaseRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");

  useEffect(() => {
    api
      .getCases(statusFilter ? { status: statusFilter } : undefined)
      .then(setCases)
      .catch((error) => {
        console.error("Failed to load cases", error);
      })
      .finally(() => setLoading(false));
  }, [statusFilter]);

  return (
    <div className="space-y-8">
      <section className="panel-card animate-in px-6 py-8 md:px-10 md:py-10">
        <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="panel-kicker">Reports / Case queue</p>
            <h1 className="section-title mt-5 text-[clamp(2.8rem,8vw,6.2rem)]">
              Review matches with AI context first
            </h1>
            <p className="panel-subtle mt-5 max-w-2xl text-base">
              Each case now leads with Gemini rationale, followed by the source,
              confidence, and draft availability so reviewers can act without
              hunting for the signal.
            </p>
          </div>

          <div className="min-w-[220px]">
            <label className="panel-kicker flex items-center gap-2">
              <Filter size={14} />
              Filter by status
            </label>
            <select
              value={statusFilter}
              onChange={(event) => {
                setLoading(true);
                setStatusFilter(event.target.value);
              }}
              className="input-field mt-2"
            >
              <option value="">All statuses</option>
              <option value="new">New</option>
              <option value="review">Reviewed</option>
              <option value="actioned">Actioned</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        </div>
      </section>

      <section className="animate-in" style={{ animationDelay: "0.05s" }}>
        <SectionDivider label="Case reports" />

        {loading ? (
          <div className="mt-4 space-y-4">
            {[1, 2, 3].map((item) => (
              <Skeleton key={item} height="260px" />
            ))}
          </div>
        ) : cases.length === 0 ? (
          <div className="mt-4">
            <EmptyState
              title="No cases in this view"
              description="Cases are created automatically when a high-confidence match is detected. Change the status filter or upload more assets to expand the queue."
            />
          </div>
        ) : (
          <div className="mt-4 space-y-4">
            {cases.map((caseItem, index) => (
              <article
                key={caseItem.id}
                className="panel-card animate-in px-6 py-6 md:px-8"
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_260px]">
                  <div className="space-y-5">
                    <div className="flex flex-wrap items-start justify-between gap-4">
                      <div>
                        <p className="panel-kicker">
                          Case ID: {caseItem.id.slice(0, 8).toUpperCase()}
                        </p>
                        <h2 className="section-title mt-4 text-[clamp(2rem,5vw,4rem)]">
                          {caseItem.detection?.asset?.title || "Untitled asset"}
                        </h2>
                        <p className="panel-subtle mt-3">
                          {caseItem.detection?.discovery?.platform || "Unknown platform"} /{" "}
                          {new Date(caseItem.created_at).toLocaleDateString()}
                        </p>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        <StatusPill status={caseItem.status} />
                        <PriorityBadge priority={caseItem.priority} />
                        {typeof caseItem.detection?.confidence === "number" ? (
                          <ScoreBadge score={caseItem.detection.confidence} />
                        ) : null}
                      </div>
                    </div>

                    <GeminiCallout
                      title="Why this match is flagged"
                      description={
                        caseItem.gemini_rationale ? (
                          <div className="whitespace-pre-line">
                            {caseItem.gemini_rationale}
                          </div>
                        ) : (
                          "Gemini content is still being generated. The underlying detection evidence and reviewer actions remain available."
                        )
                      }
                      badge={
                        caseItem.gemini_is_fallback
                          ? "Classic fallback"
                          : "Gemini-powered rationale"
                      }
                    />

                    <div className="grid gap-4 text-sm text-[var(--color-ink-soft)] md:grid-cols-2 xl:grid-cols-3">
                      <div>
                        <p className="panel-kicker">Source URL</p>
                        <a
                          href={caseItem.detection?.discovery?.source_url || "#"}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-2 inline-flex items-center gap-2 break-all text-base hover:underline"
                        >
                          {caseItem.detection?.discovery?.source_url || "Unavailable"}
                          <ExternalLink size={14} />
                        </a>
                      </div>
                      <div>
                        <p className="panel-kicker">Draft status</p>
                        <p className="mt-2 text-base">
                          {caseItem.current_draft
                            ? `${caseItem.current_draft.draft_kind} draft ready`
                            : "Waiting for draft"}
                        </p>
                      </div>
                      <div>
                        <p className="panel-kicker">AI state</p>
                        <p className="mt-2 text-base capitalize">
                          {caseItem.gemini_status.replace(/_/g, " ")}
                        </p>
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-px border border-[var(--color-line)] bg-[var(--color-line)] self-start">
                    <div className="metric-tile bg-[var(--color-success-bg)]">
                      <p className="panel-kicker">Hash</p>
                      <p className="metric-value text-[2rem]">
                        {Math.round((caseItem.detection?.hash_score || 0) * 100)}
                      </p>
                    </div>
                    <div className="metric-tile bg-[var(--color-info-bg)]">
                      <p className="panel-kicker">Embed</p>
                      <p className="metric-value text-[2rem]">
                        {Math.round((caseItem.detection?.embed_score || 0) * 100)}
                      </p>
                    </div>
                    <div className="metric-tile bg-[var(--color-warning-bg)]">
                      <p className="panel-kicker">Risk</p>
                      <p className="metric-value text-[2rem]">
                        {Math.round((caseItem.detection?.risk_score || 0) * 100)}
                      </p>
                    </div>
                    <div className="metric-tile bg-[rgba(255,255,255,0.72)]">
                      <p className="panel-kicker">Open</p>
                      <Link href={`/cases/${caseItem.id}`} className="btn-primary mt-5 w-full">
                        Open case
                      </Link>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
