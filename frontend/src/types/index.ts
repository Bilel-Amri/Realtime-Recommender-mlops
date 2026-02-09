// Real-Time Recommendation System - Type Definitions

export interface RecommendationItem {
  item_id: string;
  score: number;
  rank: number;
  reason?: string;
  metadata?: Record<string, unknown>;
}

export interface RecommendationResponse {
  user_id: string;
  recommendations: RecommendationItem[];
  model_version: string;
  model_stage: string;
  generated_at: string;
  generation_time_ms: number;
  cached: boolean;
  cold_start: boolean;
}

export enum EventType {
  VIEW = 'view',
  CLICK = 'click',
  PURCHASE = 'purchase',
  LIKE = 'like',
  DISLIKE = 'dislike',
  SHARE = 'share',
  RATING = 'rating',
}

export interface EventCreate {
  user_id: string;
  item_id: string;
  event_type: EventType;
  timestamp?: string;
  context?: Record<string, unknown>;
  value?: number;
}

export interface EventResponse {
  event_id: string;
  user_id: string;
  item_id: string;
  event_type: EventType;
  timestamp: string;
  status: string;
}

export enum HealthStatus {
  HEALTHY = 'healthy',
  DEGRADED = 'degraded',
  UNHEALTHY = 'unhealthy',
}

export interface ComponentHealth {
  name: string;
  status: HealthStatus;
  message?: string;
  latency_ms?: number;
}

export interface HealthCheckResponse {
  status: HealthStatus;
  version: string;
  timestamp: string;
  uptime_seconds: number;
  components: ComponentHealth[];
}

export enum ModelStage {
  NONE = 'None',
  STAGING = 'Staging',
  PRODUCTION = 'Production',
  ARCHIVED = 'Archived',
}

export interface ModelInfoResponse {
  name: string;
  version: string;
  stage: ModelStage;
  created_at: string;
  last_updated: string;
  metrics: Record<string, number>;
  description?: string;
  tags: Record<string, string>;
}

export interface PredictionMetrics {
  total_predictions: number;
  predictions_last_hour: number;
  average_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  cache_hit_rate: number;
  cold_start_rate: number;
}

export interface DriftMetrics {
  feature_drift_score: number;
  prediction_drift_score: number;
  last_checked: string;
  status: 'normal' | 'warning' | 'critical';
  drifted_features: string[];
}

export interface MetricsResponse {
  prediction_metrics: PredictionMetrics;
  drift_metrics: DriftMetrics;
  system_metrics: Record<string, number>;
  custom_metrics: Record<string, number>;
  timestamp: string;
}

export interface MetricsSummary {
  predictions_total: number;
  predictions_per_minute: number;
  average_latency_ms: number;
  p95_latency_ms: number;
  cache_hit_rate: number;
  cold_start_rate: number;
  model_loaded: boolean;
  uptime_seconds: number;
}

export interface TimeSeriesDataPoint {
  timestamp: string;
  value: number;
}

export interface LatencyData {
  p50: number;
  p95: number;
  p99: number;
}

export interface RecommendationRequest {
  user_id: string;
  num_recommendations: number;
  context?: Record<string, unknown>;
  exclude_items?: string[];
}
