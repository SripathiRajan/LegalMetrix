export type RuleStatus = 'PASS' | 'FAIL' | 'WARNING' | 'NOT_APPLICABLE';

export type OverallComplianceStatus = 'COMPLIANT' | 'POTENTIALLY_NON_COMPLIANT' | 'NON_COMPLIANT';

export type AuthenticityVerdict = 'GENUINE_LIKELY' | 'SUSPICIOUS' | 'NO_REFERENCE_AVAILABLE';

export type QueryIntent = 'RULE_LOOKUP' | 'DATA_QUERY' | 'HYBRID' | 'UNKNOWN';

export interface RuleEvaluationResult {
  rule_id: string;
  rule_name: string;
  status: RuleStatus;
  detected_value: string | null;
  expected_format: string | null;
  severity: 'CRITICAL' | 'MAJOR' | 'MINOR' | 'INFO';
  reason: string;
  legal_reference: string;
  source_pdf?: string | null;
  official_legal_reference?: string | null;
  is_mandatory: boolean;
  score_weight: number;
}

export interface ComplianceResponse {
  product_name?: string | null;
  overall_status: OverallComplianceStatus;
  compliance_score: number;
  total_rules_checked: number;
  passed_rules_count: number;
  failed_rules_count: number;
  warning_rules_count: number;
  results: RuleEvaluationResult[];
  summary: string;
  timestamp: string;
  is_imported: boolean;
  input_type?: string;
}

export interface EvidenceBoundingBox {
  rule_id: string;
  declaration_name: string;
  status: RuleStatus;
  bbox: number[]; // [ymin, xmin, ymax, xmax] normalized 0-1000 or absolute px
  confidence: number;
  extracted_text: string;
  font_size_px?: number | null;
  is_obscured?: boolean;
}

export interface EvidenceStatistics {
  total_declarations_found: number;
  average_ocr_confidence: number;
  min_font_size_px?: number | null;
  max_font_size_px?: number | null;
  obscured_declarations_count: number;
}

export interface VisualEvidence {
  annotated_image_base64?: string | null;
  original_dimensions: number[];
  bounding_boxes: EvidenceBoundingBox[];
  evidence_statistics: EvidenceStatistics;
}

export interface AuthenticityResult {
  brand_name?: string | null;
  similarity_score: number;
  verdict: AuthenticityVerdict;
  threshold_used: number;
  color_similarity?: number | null;
  font_height_ratio?: number | null;
  notes: string;
}

export interface ScanRecord {
  id: number;
  product_name?: string | null;
  overall_status: string;
  compliance_score: number;
  compliance_result: ComplianceResponse;
  authenticity_result?: AuthenticityResult | null;
  visual_statistics?: EvidenceStatistics | null;
  image_path?: string | null;
  officer_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface OfficerProfile {
  id: number;
  username: string;
  email?: string | null;
  badge_number?: string | null;
  role: string;
  is_active: boolean;
  created_at?: string | null;
}

export interface Token {
  access_token: string;
  token_type: string;
  expires_in_minutes: number;
  officer: OfficerProfile;
}

export interface SummaryStats {
  total_scans: number;
  compliant_scans: number;
  non_compliant_scans: number;
  compliance_rate: number;
  average_compliance_score: number;
}

export interface ViolationFieldStat {
  rule_id: string;
  declaration_name: string;
  violation_count: number;
  total_evaluations: number;
  violation_rate: number;
  source_pdf?: string | null;
}

export interface ViolationTrendPoint {
  date: string;
  total_scans: number;
  compliant_scans: number;
  non_compliant_scans: number;
  compliance_rate: number;
}

export interface BrandViolationStat {
  brand_name: string;
  total_scans: number;
  non_compliant_scans: number;
  non_compliance_rate: number;
  most_common_violation: string;
}

export interface AuthenticityFlagRate {
  total_checked: number;
  genuine_count: number;
  suspicious_count: number;
  unregistered_count: number;
  suspicious_rate: number;
}

export interface FontSizeDistribution {
  less_than_8px: number;
  between_8_and_12px: number;
  between_12_and_24px: number;
  greater_than_24px: number;
  total_measured: number;
}

export interface DashboardStatistics {
  time_range: {
    start_date: string | null;
    end_date: string | null;
  };
  summary: SummaryStats;
  violation_rate_by_field: ViolationFieldStat[];
  violation_trend_over_time: ViolationTrendPoint[];
  top_non_compliant_brands: BrandViolationStat[];
  authenticity_flag_rate: AuthenticityFlagRate;
  font_size_distribution: FontSizeDistribution;
}

export interface Citation {
  rule_id?: string | null;
  declaration_name: string;
  official_legal_reference: string;
  source_pdf?: string | null;
  english_text?: string | null;
  hindi_text_snippet?: string | null;
  last_amended_date?: string | null;
  score?: number | null;
}

export interface ChatResponse {
  query: string;
  intent: QueryIntent;
  reply: string;
  citations: Citation[];
  data_summary?: Record<string, any> | null;
  confidence: number;
}

export interface ChatRequest {
  message: string;
  context?: Record<string, any> | null;
}

export interface AnalyzeScanResponse {
  compliance_result: ComplianceResponse;
  visual_evidence?: VisualEvidence | null;
  authenticity_result?: AuthenticityResult | null;
  scan_id?: number | null;
  ocr_summary?: {
    regions_count: number;
    average_confidence: number;
    strategy_used: string;
    engine_agreement_score?: number | null;
    winning_engine?: string | null;
  } | null;
}
