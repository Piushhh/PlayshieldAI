export type CaseStatus = "new" | "review" | "actioned" | "rejected";
export type CasePriority = "low" | "medium" | "high" | "critical";

export interface ApiMessage {
  message?: string;
}

export interface UserProfileRecord {
  id: string;
  email: string;
  role: string;
  is_verified: boolean;
  email_notifications: boolean;
  created_at: string;
}

export interface AssetRecord {
  id: string;
  owner_id: string;
  title: string;
  license_type: string;
  allowed_use_notes?: string | null;
  allowed_sources_json?: string[] | null;
  media_gcs_uri?: string | null;
  media_local_path?: string | null;
  media_type: string;
  created_at: string;
  open_case_count: number;
  latest_case_id?: string | null;
  latest_case_status?: CaseStatus | null;
  latest_confidence?: number | null;
  gemini_status?: string | null;
  gemini_rationale?: string | null;
  highest_risk_label?: string | null;
}

export interface DiscoveryRecord {
  id: string;
  source_url: string;
  media_url?: string | null;
  platform?: string | null;
  captured_at: string;
  meta_json?: Record<string, unknown> | null;
}

export interface DetectionRecord {
  id: string;
  discovery_id: string;
  asset_id: string;
  hash_score: number;
  embed_score: number;
  risk_score: number;
  confidence: number;
  evidence_json?: Record<string, unknown> | null;
  created_at: string;
  discovery?: DiscoveryRecord | null;
  asset?: AssetRecord | null;
}

export interface TakedownDraftRecord {
  id: string;
  case_id: string;
  draft_text: string;
  model: string;
  draft_kind: string;
  parent_draft_id?: string | null;
  edited_by_user_id?: string | null;
  reviewed_by_user_id?: string | null;
  is_reviewed: boolean;
  reviewed_at?: string | null;
  created_at: string;
}

export interface GeminiCallRecord {
  id: string;
  case_id: string;
  actor_user_id?: string | null;
  actor_email?: string | null;
  operation: string;
  provider: string;
  model?: string | null;
  status: string;
  is_incomplete: boolean;
  error_message?: string | null;
  request_json?: Record<string, unknown> | null;
  response_json?: Record<string, unknown> | null;
  created_at: string;
  completed_at?: string | null;
}

export interface GeminiSummaryRecord {
  case_id: string;
  status: string;
  rationale?: string | null;
  model?: string | null;
  provider?: string | null;
  error_message?: string | null;
  incomplete_reason?: string | null;
  is_incomplete: boolean;
  is_fallback: boolean;
  generated_at?: string | null;
  last_attempted_at?: string | null;
  current_draft?: TakedownDraftRecord | null;
  draft_history: TakedownDraftRecord[];
  recent_calls: GeminiCallRecord[];
}

export interface CaseRecord {
  id: string;
  detection_id: string;
  owner_id?: string | null;
  status: CaseStatus;
  priority: CasePriority;
  assigned_to?: string | null;
  created_at: string;
  updated_at: string;
  gemini_status?: string | null;
  gemini_rationale?: string | null;
  gemini_model?: string | null;
  gemini_provider?: string | null;
  gemini_error?: string | null;
  gemini_incomplete_reason?: string | null;
  gemini_is_incomplete?: boolean;
  gemini_is_fallback?: boolean;
  gemini_last_attempted_at?: string | null;
  gemini_generated_at?: string | null;
  detection?: DetectionRecord | null;
  takedown_drafts?: TakedownDraftRecord[] | null;
  current_draft?: TakedownDraftRecord | null;
}

export interface DashboardInsightCard {
  title: string;
  value: number;
  trend: string;
  tone: string;
  subtitle: string;
}

export interface DashboardStatsRecord {
  total_assets: number;
  total_scans: number;
  open_cases: number;
  total_detections: number;
  high_confidence_count: number;
  medium_confidence_count: number;
  low_confidence_count: number;
  trend_data?: Array<{
    date: string;
    detections: number;
    cases: number;
  }> | null;
  top_flagged_sources?: DashboardInsightCard[] | null;
  gemini_overview?: DashboardInsightCard[] | null;
}


export interface AuditLogRecord {
  id: string;
  actor_user_id?: string | null;
  actor_email?: string | null;
  entity_type: string;
  entity_id: string;
  action: string;
  before_json?: Record<string, unknown> | null;
  after_json?: Record<string, unknown> | null;
  created_at: string;
}

export interface NotificationRecord {
  id: string;
  user_id: string;
  title: string;
  message: string;
  case_id?: string | null;
  is_read: boolean;
  created_at: string;
}

export interface CrawlRunResponse {
  task_id?: string;
  message?: string;
}

export interface AlertsTestResponse {
  slack?: string | boolean;
  email?: string | boolean;
  message?: string;
}
