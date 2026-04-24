/**
 * PlayShield AI — API Client
 * Handles all communication with the FastAPI backend.
 */

import type {
  AlertsTestResponse,
  ApiMessage,
  AssetRecord,
  AuditLogRecord,
  CaseRecord,
  CrawlRunResponse,
  DashboardStatsRecord,
  DetectionRecord,
  GeminiSummaryRecord,
  NotificationRecord,
  TakedownDraftRecord,
  UserProfileRecord,
} from "@/lib/types";

const API_BASE = "https://playshield-backend-nfzz4olvxq-uc.a.run.app";

interface TokenPair {
  access_token: string;
  refresh_token: string;
}

class ApiClient {
  private accessToken: string | null = null;
  private refreshToken: string | null = null;

  constructor() {
    if (typeof window !== "undefined") {
      this.accessToken = localStorage.getItem("access_token");
      this.refreshToken = localStorage.getItem("refresh_token");
    }
  }

  setTokens(tokens: TokenPair) {
    this.accessToken = tokens.access_token;
    this.refreshToken = tokens.refresh_token;
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
    }
  }

  clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
  }

  isAuthenticated(): boolean {
    return !!this.accessToken;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };
    if (this.accessToken) {
      headers["Authorization"] = `Bearer ${this.accessToken}`;
    }
    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    if (res.status === 401 && this.refreshToken) {
      // Try refresh
      const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      });
      if (refreshRes.ok) {
        const tokens = (await refreshRes.json()) as TokenPair;
        this.setTokens(tokens);
        headers["Authorization"] = `Bearer ${tokens.access_token}`;
        const retryRes = await fetch(`${API_BASE}${path}`, {
          ...options,
          headers,
        });
        if (!retryRes.ok) throw new Error(`API Error: ${retryRes.status}`);
        return retryRes.json();
      } else {
        this.clearTokens();
        if (typeof window !== "undefined") window.location.href = "/login";
        throw new Error("Session expired");
      }
    }

    if (!res.ok) {
      const errorBody = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(errorBody.detail || `API Error ${res.status}`);
    }
    if (res.headers.get("content-type")?.includes("text/")) {
      return (await res.text()) as unknown as T;
    }
    return res.json();
  }

  // ── Auth ─────────────────────────────
  async register(email: string, password: string) {
    return this.request<UserProfileRecord>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  }

  async verifyEmail(token: string) {
    return this.request<ApiMessage>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token }),
    });
  }

  async login(email: string, password: string) {
    const tokens = await this.request<TokenPair>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    this.setTokens(tokens);
    return tokens;
  }

  async forgotPassword(email: string) {
    return this.request<ApiMessage>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  }

  async resetPassword(token: string, newPassword: string) {
    return this.request<ApiMessage>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    });
  }

  async getMe() {
    return this.request<UserProfileRecord>("/auth/me");
  }

  // ── Dashboard ────────────────────────
  async getDashboardStats() {
    return this.request<DashboardStatsRecord>("/dashboard/stats");
  }

  // ── Assets ───────────────────────────
  async getAssets() {
    return this.request<AssetRecord[]>("/assets");
  }

  async uploadAsset(formData: FormData) {
    return this.request<AssetRecord>("/assets/upload", {
      method: "POST",
      body: formData,
    });
  }

  async deleteAsset(id: string) {
    return this.request<ApiMessage>(`/assets/${id}`, { method: "DELETE" });
  }

  // ── Cases ────────────────────────────
  async getCases(params?: { status?: string; min_confidence?: number }) {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.min_confidence)
      qs.set("min_confidence", String(params.min_confidence));
    const query = qs.toString() ? `?${qs}` : "";
    return this.request<CaseRecord[]>(`/cases${query}`);
  }

  async getCase(id: string) {
    return this.request<CaseRecord>(`/cases/${id}`);
  }

  async decideCase(id: string, status: string, notes?: string) {
    return this.request<CaseRecord>(`/cases/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ status, notes }),
    });
  }

  async generateDraft(caseId: string) {
    return this.request<TakedownDraftRecord>(`/cases/${caseId}/generate-draft`, {
      method: "POST",
    });
  }

  async getGeminiSummary(caseId: string) {
    return this.request<GeminiSummaryRecord>(`/cases/${caseId}/gemini-summary`);
  }

  async generateGemini(caseId: string) {
    return this.request<GeminiSummaryRecord>(`/cases/${caseId}/generate-gemini`, {
      method: "POST",
    });
  }

  async updateDraft(caseId: string, draftId: string, draftText: string) {
    return this.request<TakedownDraftRecord>(`/cases/${caseId}/drafts/${draftId}`, {
      method: "PATCH",
      body: JSON.stringify({ draft_text: draftText }),
    });
  }

  async reviewDraft(caseId: string, draftId: string) {
    return this.request<TakedownDraftRecord>(`/cases/${caseId}/drafts/${draftId}/review`, {
      method: "POST",
    });
  }

  async exportDraft(caseId: string, format: "txt" | "md" = "txt") {
    return this.request<string>(
      `/cases/${caseId}/export-draft?format=${format}`
    );
  }

  // ── Detections ───────────────────────
  async getDetections(minConfidence?: number) {
    const qs = minConfidence ? `?min_confidence=${minConfidence}` : "";
    return this.request<DetectionRecord[]>(`/detections${qs}`);
  }

  // ── Crawl & Scan ─────────────────────
  async runCrawl(sources?: string[]) {
    return this.request<CrawlRunResponse>("/crawl/run", {
      method: "POST",
      body: JSON.stringify(sources ? { sources } : {}),
    });
  }

  async runScan(discoveryIds?: string[]) {
    return this.request<CrawlRunResponse>("/scan/run", {
      method: "POST",
      body: JSON.stringify(discoveryIds ? { discovery_ids: discoveryIds } : {}),
    });
  }

  // ── Alerts ───────────────────────────
  async testAlerts() {
    return this.request<AlertsTestResponse>("/alerts/test", { method: "POST" });
  }

  // ── Audit ────────────────────────────
  async getAuditLogs(params?: { entity_type?: string; entity_id?: string }) {
    const qs = new URLSearchParams();
    if (params?.entity_type) qs.set("entity_type", params.entity_type);
    if (params?.entity_id) qs.set("entity_id", params.entity_id);
    const query = qs.toString() ? `?${qs}` : "";
    return this.request<AuditLogRecord[]>(`/audit-logs${query}`);
  }

  // ── Notifications ───────────────────
  async getNotifications(unreadOnly: boolean = false) {
    return this.request<NotificationRecord[]>(
      `/notifications${unreadOnly ? "?unread_only=true" : ""}`
    );
  }

  async getUnreadCount() {
    return this.request<{ unread_count: number }>("/notifications/count");
  }

  async markNotificationRead(id: string) {
    return this.request<ApiMessage>(`/notifications/${id}/read`, { method: "POST" });
  }

  async markAllNotificationsRead() {
    return this.request<ApiMessage>("/notifications/read-all", { method: "POST" });
  }

  // ── Account ──────────────────────────
  async getAccountSettings() {
    return this.request<UserProfileRecord>("/account/settings");
  }

  async updateAccountSettings(settings: { email_notifications?: boolean }) {
    return this.request<UserProfileRecord>("/account/settings", {
      method: "PATCH",
      body: JSON.stringify(settings),
    });
  }

  async deleteAccount() {
    return this.request<ApiMessage>("/account/delete", { method: "DELETE" });
  }

  // ── Generic Helpers ──────────────────
  async get<T>(path: string, options: RequestInit = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: "GET" });
  }

  async post<T>(path: string, body?: any, options: RequestInit = {}): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async patch<T>(path: string, body?: any, options: RequestInit = {}): Promise<T> {
    return this.request<T>(path, {
      ...options,
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  async delete<T>(path: string, options: RequestInit = {}): Promise<T> {
    return this.request<T>(path, { ...options, method: "DELETE" });
  }
}

export const api = new ApiClient();
