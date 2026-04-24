"use client";

import { useEffect, useState } from "react";
import { ChevronDown, ChevronUp, Film, Image as ImageIcon, Plus } from "lucide-react";
import { api } from "@/lib/api";
import type { AssetRecord } from "@/lib/types";
import {
  EmptyState,
  ErrorState,
  GeminiCallout,
  Modal,
  ScoreBadge,
  SectionDivider,
  Skeleton,
  StatusPill,
} from "@/components/ui";

function shortRegistryId(id: string) {
  return id.slice(0, 8).toUpperCase();
}

export default function AssetsPage() {
  const [assets, setAssets] = useState<AssetRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [showUpload, setShowUpload] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [expandedAssetId, setExpandedAssetId] = useState<string | null>(null);
  const [scanningAssetIds, setScanningAssetIds] = useState<Set<string>>(new Set());

  const loadAssets = () => {
    setLoading(true);
    api
      .getAssets()
      .then(setAssets)
      .catch((currentError: Error) => setError(currentError.message))
      .finally(() => setLoading(false));
  };

  const handleRunScan = async (assetId: string) => {
    setScanningAssetIds((prev) => new Set(prev).add(assetId));
    try {
      // POST /assets/{id}/analyze
      await api.post(`/assets/${assetId}/analyze`, {});
      await loadAssets();
    } catch (currentError) {
      console.error("AI Scan failed", currentError);
      setError(currentError instanceof Error ? currentError.message : "AI Scan failed");
    } finally {
      setScanningAssetIds((prev) => {
        const next = new Set(prev);
        next.delete(assetId);
        return next;
      });
    }
  };

  useEffect(() => {
    const loadInitialAssets = async () => {
      try {
        const assetResponse = await api.getAssets();
        setAssets(assetResponse ?? []);
      } catch (currentError) {
        console.error("Initial load failed", currentError);
        setError(currentError instanceof Error ? currentError.message : "Unable to load assets");
      } finally {
        setLoading(false);
      }
    };

    void loadInitialAssets();
  }, []);

  const handleUpload = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setUploading(true);
    setError(""); // Clear previous errors
    try {
      // Use the dedicated upload route
      await api.uploadAsset(form);
      setShowUpload(false);
      loadAssets();
    } catch (currentError) {
      console.error("Upload failed", currentError);
      setError(currentError instanceof Error ? currentError.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-8">
      <section className="panel-card animate-in px-6 py-8 md:px-10 md:py-10">
        <div className="flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-3xl">
            <p className="panel-kicker">Registry / Protected assets</p>
            <h1 className="section-title mt-5 text-[clamp(2.8rem,8vw,6.4rem)]">
              Build a clear protection registry
            </h1>
            <p className="panel-subtle mt-5 max-w-2xl text-base">
              Every asset card surfaces the strongest active signal, the latest Gemini
              rationale, and the case state attached to that asset so teams can scan
              risk without drilling into each record.
            </p>
          </div>

          <button onClick={() => setShowUpload(true)} className="btn-primary">
            <Plus size={16} /> New protection
          </button>
        </div>
      </section>

      <section className="animate-in" style={{ animationDelay: "0.05s" }}>
        <SectionDivider label="Asset registry" />

        {error ? <div className="mt-4"><ErrorState message={error} onRetry={loadAssets} /></div> : null}

        {loading ? (
          <div className="mt-4 grid grid-cols-1 gap-5 xl:grid-cols-2">
            {[1, 2, 3, 4].map((item) => (
              <Skeleton key={item} height="340px" />
            ))}
          </div>
        ) : assets.length === 0 ? (
          <div className="mt-4">
            <EmptyState
              title="No protected assets yet"
              description="Upload your first image or video asset and PlayShield will start fingerprinting, monitoring, and preparing Gemini rationale for new cases."
              action={
                <button onClick={() => setShowUpload(true)} className="btn-primary">
                  <Plus size={16} /> Upload asset
                </button>
              }
            />
          </div>
        ) : (
          <div className="mt-4 grid grid-cols-1 gap-5 xl:grid-cols-2">
            {assets.map((asset, index) => {
              const expanded = expandedAssetId === asset.id;
              return (
                <article
                  key={asset.id}
                  className="panel-card animate-in overflow-hidden"
                  style={{ animationDelay: `${index * 0.06}s` }}
                >
                  <div className="border-b border-[var(--color-line)] px-6 py-4">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="panel-kicker">Registry ID: {shortRegistryId(asset.id)}</p>
                        <h2 className="section-title mt-5 text-[clamp(2rem,4vw,3.7rem)]">
                          {asset.title}
                        </h2>
                      </div>

                      <div className="flex h-14 w-14 items-center justify-center border border-[var(--color-line)] bg-[rgba(255,255,255,0.72)]">
                        {asset.media_type === "video" ? (
                          <Film size={24} />
                        ) : (
                          <ImageIcon size={24} />
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="grid gap-6 px-6 py-6 md:grid-cols-[minmax(0,1fr)_220px]">
                    <div className="space-y-5">
                      <div className="grid gap-3 text-sm text-[var(--color-ink-soft)] sm:grid-cols-2">
                        <div>
                          <p className="panel-kicker">Media type</p>
                          <p className="mt-2 text-base uppercase">{asset.media_type}</p>
                        </div>
                        <div>
                          <p className="panel-kicker">License</p>
                          <p className="mt-2 text-base">{asset.license_type}</p>
                        </div>
                        <div>
                          <p className="panel-kicker">Created</p>
                          <p className="mt-2 text-base">
                            {new Date(asset.created_at).toLocaleDateString()}
                          </p>
                        </div>
                        <div>
                          <p className="panel-kicker">Cases</p>
                          <p className="mt-2 text-base">{asset.open_case_count} open</p>
                        </div>
                      </div>

                      {asset.gemini_rationale ? (
                        <GeminiCallout
                          title="Why this asset is being watched"
                          description={
                            <div className="space-y-2 whitespace-pre-line text-sm md:text-base leading-relaxed font-normal">
                              {expanded
                                ? asset.gemini_rationale
                                : `${asset.gemini_rationale.slice(0, 180)}${
                                    asset.gemini_rationale.length > 180 ? "..." : ""
                                  }`}
                            </div>
                          }
                          className="shadow-none border-[var(--color-line)]"
                        />
                      ) : (
                        <div className="panel-card border-dashed bg-[var(--color-info-bg)] p-5">
                          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                            <div>
                              <p className="font-bold text-[var(--color-info-text)]">
                                Gemini rationale missing
                              </p>
                              <p className="mt-1 text-sm text-[var(--color-ink-soft)]">
                                No AI risk analysis has been performed for this asset yet.
                              </p>
                            </div>
                            <button
                              onClick={() => handleRunScan(asset.id)}
                              disabled={scanningAssetIds.has(asset.id)}
                              className="btn-primary whitespace-nowrap"
                            >
                              {scanningAssetIds.has(asset.id) ? "Scanning..." : "Run AI Risk Scan"}
                            </button>
                          </div>
                        </div>
                      )}

                      <div className="flex items-center gap-4">
                        <button
                          onClick={() =>
                            setExpandedAssetId(expanded ? null : asset.id)
                          }
                          className="btn-secondary"
                        >
                          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                          {expanded ? "Collapse rationale" : "Expand rationale"}
                        </button>
                        
                        {asset.gemini_rationale && (
                           <button
                            onClick={() => handleRunScan(asset.id)}
                            disabled={scanningAssetIds.has(asset.id)}
                            className="text-xs font-bold uppercase tracking-wider text-[var(--color-ink-soft)] hover:text-[var(--color-ink)] disabled:opacity-50"
                          >
                            {scanningAssetIds.has(asset.id) ? "Refreshing..." : "Re-run AI Scan"}
                          </button>
                        )}
                      </div>
                    </div>

                    <div className="grid grid-cols-1 gap-px border border-[var(--color-line)] bg-[var(--color-line)] sm:grid-cols-2 md:grid-cols-1 xl:grid-cols-2">
                      <div className="metric-tile bg-[var(--color-success-bg)]">
                        <p className="panel-kicker">Confidence</p>
                        <div className="mt-4 overflow-hidden truncate">
                          {typeof asset.latest_confidence === "number" ? (
                            <ScoreBadge score={asset.latest_confidence} />
                          ) : (
                            <p className="metric-value">--</p>
                          )}
                        </div>
                      </div>
                      <div className="metric-tile bg-[var(--color-info-bg)]">
                        <p className="panel-kicker">Risk</p>
                        <p className="metric-value truncate">
                          {asset.highest_risk_label || "Waiting"}
                        </p>
                      </div>
                      <div className="metric-tile bg-[rgba(255,255,255,0.72)]">
                        <p className="panel-kicker">Case state</p>
                        <div className="mt-4 overflow-hidden truncate">
                          {asset.latest_case_status ? (
                            <StatusPill status={asset.latest_case_status} />
                          ) : (
                            <span className="status-pill">No cases</span>
                          )}
                        </div>
                      </div>
                      <div className="metric-tile bg-[var(--color-warning-bg)]">
                        <p className="panel-kicker">AI status</p>
                        <p className="metric-value truncate">
                          {asset.gemini_status || "Pending"}
                        </p>
                      </div>
                    </div>

                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      <Modal open={showUpload} onClose={() => setShowUpload(false)} title="Register protected asset">
        <form onSubmit={handleUpload} className="space-y-5">
          <div className="grid gap-5 md:grid-cols-2">
            <div>
              <label className="panel-kicker">Asset title</label>
              <input name="title" required className="input-field mt-2" placeholder="Kinetic Infrastructure" />
            </div>
            <div>
              <label className="panel-kicker">License</label>
              <select name="license_type" className="input-field mt-2">
                <option value="all_rights_reserved">All Rights Reserved</option>
                <option value="creative_commons">Creative Commons</option>
                <option value="commercial">Commercial License</option>
              </select>
            </div>
            <div>
              <label className="panel-kicker">Asset type</label>
              <select name="media_type" className="input-field mt-2">
                <option value="image">Image</option>
                <option value="video">Video</option>
              </select>
            </div>
            <div>
              <label className="panel-kicker">File upload</label>
              <input
                name="file"
                type="file"
                required
                accept="image/*,video/*"
                className="input-field mt-2"
              />
            </div>
          </div>

          <div className="rounded-none border border-[var(--color-line)] bg-[var(--color-info-bg)] px-4 py-3 text-sm text-[var(--color-ink-soft)]">
            New detections generated from this asset will automatically request Gemini
            rationale and a draft takedown letter when case creation is triggered.
          </div>

          <div className="flex flex-wrap justify-end gap-3">
            <button type="button" onClick={() => setShowUpload(false)} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={uploading} className="btn-primary">
              {uploading ? "Registering..." : "Register asset"}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
