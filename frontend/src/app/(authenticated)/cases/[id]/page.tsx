"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Bot,
  Copy,
  Download,
  ExternalLink,
  FileText,
  Save,
  Shield,
  Sparkles,
  Stamp,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import type {
  AuditLogRecord,
  CaseRecord,
  GeminiSummaryRecord,
} from "@/lib/types";
import {
  Callout,
  DraftReviewedBadge,
  GeminiCallout,
  Modal,
  Panel,
  PriorityBadge,
  ScoreBadge,
  SectionDivider,
  Skeleton,
  StatusPill,
  StickyActionBar,
} from "@/components/ui";

function formatAction(action: string) {
  return action.replace(/_/g, " ");
}

function latestDraft(caseData: CaseRecord | null, summary: GeminiSummaryRecord | null) {
  return (
    summary?.current_draft ||
    caseData?.current_draft ||
    caseData?.takedown_drafts?.slice().sort((left, right) => {
      return new Date(right.created_at).getTime() - new Date(left.created_at).getTime();
    })[0] ||
    null
  );
}

export default function CaseDetailPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = params.id as string;

  const [caseData, setCaseData] = useState<CaseRecord | null>(null);
  const [summary, setSummary] = useState<GeminiSummaryRecord | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLogRecord[]>([]);
  const [draftText, setDraftText] = useState("");
  const [loading, setLoading] = useState(true);
  const [generateModalOpen, setGenerateModalOpen] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [decisionLoading, setDecisionLoading] = useState("");
  const [copyState, setCopyState] = useState("Copy draft");

  const currentDraft = useMemo(() => latestDraft(caseData, summary), [caseData, summary]);
  const draftDirty = !!currentDraft && draftText !== currentDraft.draft_text;

  useEffect(() => {
    const loadInitialCase = async () => {
      try {
        const [caseResponse, summaryResponse, auditResponse] = await Promise.all([
          api.getCase(caseId),
          api.getGeminiSummary(caseId),
          api.getAuditLogs({ entity_type: "case", entity_id: caseId }),
        ]);

        setCaseData(caseResponse);
        setSummary(summaryResponse);
        setAuditLogs(auditResponse);
        const resolvedDraft = latestDraft(caseResponse, summaryResponse);
        setDraftText(resolvedDraft?.draft_text || "");
      } catch (error) {
        console.error("Failed to load case detail", error);
      } finally {
        setLoading(false);
      }
    };

    void loadInitialCase();
  }, [caseId]);

  const handleDecision = async (status: "actioned" | "rejected") => {
    setDecisionLoading(status);
    try {
      const updatedCase = await api.decideCase(caseId, status);
      setCaseData(updatedCase);
      const nextAuditLogs = await api.getAuditLogs({
        entity_type: "case",
        entity_id: caseId,
      });
      setAuditLogs(nextAuditLogs);
    } finally {
      setDecisionLoading("");
    }
  };

  const handleGenerateGemini = async () => {
    setGenerating(true);
    try {
      const summaryResponse = await api.generateGemini(caseId);
      setSummary(summaryResponse);
      const refreshedCase = await api.getCase(caseId);
      setCaseData(refreshedCase);
      const nextAuditLogs = await api.getAuditLogs({
        entity_type: "case",
        entity_id: caseId,
      });
      setAuditLogs(nextAuditLogs);
      const resolvedDraft = latestDraft(refreshedCase, summaryResponse);
      setDraftText(resolvedDraft?.draft_text || "");
      setGenerateModalOpen(false);
    } finally {
      setGenerating(false);
    }
  };

  const handleSaveDraft = async () => {
    if (!currentDraft) return;
    setSaving(true);
    try {
      await api.updateDraft(caseId, currentDraft.id, draftText);
      const [nextSummary, nextCase, nextAuditLogs] = await Promise.all([
        api.getGeminiSummary(caseId),
        api.getCase(caseId),
        api.getAuditLogs({ entity_type: "case", entity_id: caseId }),
      ]);
      setSummary(nextSummary);
      setCaseData(nextCase);
      setAuditLogs(nextAuditLogs);
      const resolvedDraft = latestDraft(nextCase, nextSummary);
      setDraftText(resolvedDraft?.draft_text || "");
    } finally {
      setSaving(false);
    }
  };

  const handleReviewDraft = async () => {
    if (!currentDraft) return;
    setReviewing(true);
    try {
      await api.reviewDraft(caseId, currentDraft.id);
      const [nextSummary, nextCase, nextAuditLogs] = await Promise.all([
        api.getGeminiSummary(caseId),
        api.getCase(caseId),
        api.getAuditLogs({ entity_type: "case", entity_id: caseId }),
      ]);
      setSummary(nextSummary);
      setCaseData(nextCase);
      setAuditLogs(nextAuditLogs);
      const resolvedDraft = latestDraft(nextCase, nextSummary);
      setDraftText(resolvedDraft?.draft_text || "");
    } finally {
      setReviewing(false);
    }
  };

  const handleExport = async (format: "txt" | "md") => {
    const text = await api.exportDraft(caseId, format);
    const blob = new Blob([text], {
      type: format === "md" ? "text/markdown" : "text/plain",
    });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `takedown_draft_${caseId}.${format}`;
    anchor.click();
    URL.revokeObjectURL(url);

    const nextAuditLogs = await api.getAuditLogs({
      entity_type: "case",
      entity_id: caseId,
    });
    setAuditLogs(nextAuditLogs);
  };

  const handleCopy = async () => {
    if (!draftText) return;
    await navigator.clipboard.writeText(draftText);
    setCopyState("Copied");
    window.setTimeout(() => setCopyState("Copy draft"), 1400);
  };

  if (loading || !caseData) {
    return (
      <div className="space-y-6">
        <Skeleton height="88px" />
        <Skeleton height="200px" />
        <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.2fr)_400px]">
          <Skeleton height="620px" />
          <div className="space-y-6">
            <Skeleton height="260px" />
            <Skeleton height="320px" />
          </div>
        </div>
      </div>
    );
  }

  const detection = caseData.detection;
  const evidence = detection?.evidence_json || {};

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-4 animate-in">
        <div className="flex items-center gap-3">
          <button onClick={() => router.push("/cases")} className="btn-secondary">
            <ArrowLeft size={16} /> Back
          </button>
          <div>
            <p className="panel-kicker">Case file / {caseId.slice(0, 8).toUpperCase()}</p>
            <h1 className="section-title mt-3 text-[clamp(2.2rem,6vw,4.8rem)]">
              {detection?.asset?.title || "Case detail"}
            </h1>
          </div>
        </div>

        <div className="flex flex-wrap gap-2">
          <StatusPill status={caseData.status} />
          <PriorityBadge priority={caseData.priority} />
          {typeof detection?.confidence === "number" ? (
            <ScoreBadge score={detection.confidence} />
          ) : null}
          {currentDraft?.is_reviewed ? <DraftReviewedBadge /> : null}
        </div>
      </div>

      {summary?.rationale ? (
        <GeminiCallout
          title="Why this match?"
          description={<div className="whitespace-pre-line">{summary.rationale}</div>}
          badge={
            summary.is_fallback ? "Classic fallback explanation" : "Gemini-powered rationale"
          }
          className="animate-in"
        />
      ) : (
        <div className="panel-card animate-in p-6">
          <p className="panel-kicker">Gemini-powered rationale</p>
          <div className="mt-4 space-y-3">
            <Skeleton height="24px" width="40%" />
            <Skeleton height="18px" />
            <Skeleton height="18px" />
            <Skeleton height="18px" width="85%" />
          </div>
        </div>
      )}

      {summary?.is_incomplete || summary?.error_message ? (
        <Callout
          title="AI services delayed"
          badge="Non-blocking fallback"
          tone="warning"
          description={
            <div className="space-y-2">
              <p>
                {summary.incomplete_reason ||
                  "AI generation is incomplete right now. Review, export, and status actions remain available."}
              </p>
              {summary.error_message ? (
                <p className="font-['IBM_Plex_Mono'] text-xs uppercase tracking-[0.16em]">
                  Error: {summary.error_message}
                </p>
              ) : null}
            </div>
          }
        />
      ) : null}

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.22fr)_400px]">
        <Panel
          kicker="Editable takedown letter"
          title="Draft letter"
          className="animate-in p-6"
          actions={
            <div className="flex flex-wrap gap-2">
              {summary?.model ? (
                <span className="micro-badge">{summary.model}</span>
              ) : null}
              {summary?.generated_at ? (
                <span className="micro-badge">
                  {new Date(summary.generated_at).toLocaleString()}
                </span>
              ) : null}
            </div>
          }
        >
          <div className="space-y-4">
            <GeminiCallout
              title="Draft guidance"
              description="This panel is editable. Saving creates a new audited draft revision, and the original AI output remains preserved for comparison."
              badge="Audit-safe editing"
            />

            <textarea
              value={draftText}
              onChange={(event) => setDraftText(event.target.value)}
              className="input-field min-h-[480px] resize-y font-['IBM_Plex_Mono'] text-sm leading-7"
              placeholder="Generate a Gemini draft to start editing here."
            />
          </div>
        </Panel>

        <div className="space-y-6">
          <Panel kicker="Signal breakdown" title="Evidence and scores" className="animate-in p-6">
            <div className="space-y-5">
              {[
                { label: "Overall confidence", value: detection?.confidence || 0 },
                { label: "Hash similarity", value: detection?.hash_score || 0 },
                { label: "Embedding similarity", value: detection?.embed_score || 0 },
                { label: "Risk score", value: detection?.risk_score || 0 },
              ].map((item) => (
                <div key={item.label}>
                  <div className="mb-2 flex items-center justify-between gap-4">
                    <p className="panel-kicker">{item.label}</p>
                    <ScoreBadge score={item.value} />
                  </div>
                  <div className="h-3 border border-[var(--color-line)] bg-[rgba(255,255,255,0.65)]">
                    <div
                      className="h-full bg-[var(--color-info-bg)]"
                      style={{ width: `${Math.round(item.value * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </Panel>

          <Panel kicker="Source evidence" title="Asset and discovery" className="animate-in p-6">
            <div className="space-y-4 text-sm text-[var(--color-ink-soft)]">
              <div>
                <p className="panel-kicker">Asset</p>
                <p className="mt-2 text-base text-[var(--color-ink)]">
                  {detection?.asset?.title || "Unknown"}
                </p>
              </div>
              <div>
                <p className="panel-kicker">License</p>
                <p className="mt-2 text-base text-[var(--color-ink)]">
                  {detection?.asset?.license_type || "Unknown"}
                </p>
              </div>
              <div>
                <p className="panel-kicker">Platform</p>
                <p className="mt-2 text-base text-[var(--color-ink)]">
                  {detection?.discovery?.platform || "Unknown"}
                </p>
              </div>
              <div>
                <p className="panel-kicker">Source URL</p>
                <a
                  href={detection?.discovery?.source_url || "#"}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-flex items-center gap-2 break-all text-base text-[var(--color-ink)] hover:underline"
                >
                  {detection?.discovery?.source_url || "Unavailable"}
                  <ExternalLink size={14} />
                </a>
              </div>
              <div>
                <p className="panel-kicker">Evidence snapshot</p>
                <pre className="mt-2 overflow-x-auto border border-[var(--color-line)] bg-[rgba(255,255,255,0.72)] p-4 font-['IBM_Plex_Mono'] text-xs leading-6 text-[var(--color-ink-soft)]">
                  {JSON.stringify(evidence, null, 2)}
                </pre>
              </div>
            </div>
          </Panel>
        </div>
      </div>

      <Panel kicker="Audit trail" title="Generation, edit, export, review" className="animate-in p-6">
        <SectionDivider label="Latest events" />
        <div className="mt-5 space-y-4">
          {auditLogs.length === 0 ? (
            <Callout
              title="No audit events yet"
              description="Generate a Gemini draft, edit the letter, or export it to see audited actions appear here."
              tone="info"
            />
          ) : (
            auditLogs.map((log) => (
              <div key={log.id} className="border border-[var(--color-line)] bg-[rgba(255,255,255,0.68)] p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2">
                    <span className="micro-badge">{formatAction(log.action)}</span>
                    <span className="panel-kicker">
                      {log.actor_email || "System"}
                    </span>
                  </div>
                  <span className="panel-kicker">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                </div>
                {log.after_json ? (
                  <pre className="mt-4 overflow-x-auto border border-[var(--color-line-soft)] bg-[rgba(255,255,255,0.74)] p-3 font-['IBM_Plex_Mono'] text-xs leading-6 text-[var(--color-ink-soft)]">
                    {JSON.stringify(log.after_json, null, 2)}
                  </pre>
                ) : null}
              </div>
            ))
          )}
        </div>
      </Panel>

      <StickyActionBar className="animate-in">
        <button onClick={() => setGenerateModalOpen(true)} className="btn-primary">
          <Sparkles size={16} /> Generate Gemini draft
        </button>
        <button
          onClick={handleSaveDraft}
          className="btn-secondary"
          disabled={!currentDraft || !draftDirty || saving}
        >
          <Save size={16} /> {saving ? "Saving..." : "Save edits"}
        </button>
        <button onClick={handleCopy} className="btn-secondary" disabled={!draftText}>
          <Copy size={16} /> {copyState}
        </button>
        <button
          onClick={() => handleExport("txt")}
          className="btn-secondary"
          disabled={!currentDraft}
        >
          <Download size={16} /> Export .txt
        </button>
        <button
          onClick={() => handleExport("md")}
          className="btn-secondary"
          disabled={!currentDraft}
        >
          <FileText size={16} /> Export .md
        </button>
        <button
          onClick={handleReviewDraft}
          className="btn-success"
          disabled={!currentDraft || currentDraft.is_reviewed || reviewing}
        >
          <Stamp size={16} /> {reviewing ? "Reviewing..." : "Mark as reviewed"}
        </button>
        <button
          onClick={() => handleDecision("actioned")}
          className="btn-success"
          disabled={decisionLoading.length > 0}
        >
          <Shield size={16} /> {decisionLoading === "actioned" ? "Working..." : "Approve"}
        </button>
        <button
          onClick={() => handleDecision("rejected")}
          className="btn-danger"
          disabled={decisionLoading.length > 0}
        >
          <XCircle size={16} /> {decisionLoading === "rejected" ? "Working..." : "Reject"}
        </button>
      </StickyActionBar>

      <Modal
        open={generateModalOpen}
        onClose={() => setGenerateModalOpen(false)}
        title="Generate Gemini draft"
      >
        <div className="space-y-5">
          <Callout
            title="Gemini will use the full case context"
            badge="AI action"
            tone="info"
            icon={<Bot size={18} />}
            description="Asset metadata, evidence payloads, confidence/risk scores, and discovery details will be sent to Vertex AI Gemini so it can refresh both the rationale card and the takedown draft."
          />

          <div className="border border-[var(--color-line)] bg-[var(--color-warning-bg)] px-4 py-4 text-sm leading-7 text-[var(--color-ink-soft)]">
            AI-generated content should always be reviewed by a human before it is sent.
            Generating again preserves earlier drafts in the audit trail instead of overwriting
            them.
          </div>

          <div className="flex flex-wrap justify-end gap-3">
            <button onClick={() => setGenerateModalOpen(false)} className="btn-secondary">
              Cancel
            </button>
            <button onClick={handleGenerateGemini} className="btn-primary" disabled={generating}>
              <Sparkles size={16} />
              {generating ? "Generating..." : "Generate now"}
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
