// Real-Time Recommendation System - API Service
/**
 * API client for the recommendation system backend.
 *
 * This module provides typed API calls to the backend services:
 * - Recommendations: Get personalized item recommendations
 * - Events: Log user interaction events
 * - Metrics: Retrieve system metrics and monitoring data
 * - Health: Check service health status
 *
 * All endpoints use Axios for HTTP communication with proper
 * error handling and type safety.
 */

import axios, { AxiosInstance, AxiosError } from 'axios';
import type {
  RecommendationResponse,
  RecommendationRequest,
  EventCreate,
  EventResponse,
  HealthCheckResponse,
  ModelInfoResponse,
  MetricsResponse,
  MetricsSummary,
} from '../types';

// API Configuration
const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/v1';

// Create axios instance with default config
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    console.error('[API] Response error:', error.message);
    return Promise.reject(error);
  }
);

/**
 * Recommendation API
 */
export const recommendationApi = {
  /**
   * Get personalized recommendations for a user.
   *
   * @param request - Recommendation request with user_id and parameters
   * @returns Promise with recommendation response
   *
   * @example
   * const response = await recommendationApi.getRecommendations({
   *   user_id: 'user_123',
   *   num_recommendations: 10
   * });
   */
  async getRecommendations(request: RecommendationRequest): Promise<RecommendationResponse> {
    const response = await apiClient.post<RecommendationResponse>('/recommend', request);
    return response.data;
  },

  /**
   * Get current model information.
   *
   * @returns Promise with model information
   *
   * @example
   * const modelInfo = await recommendationApi.getModelInfo();
   * console.log(modelInfo.version, modelInfo.stage);
   */
  async getModelInfo(): Promise<ModelInfoResponse> {
    const response = await apiClient.get<ModelInfoResponse>('/model-info');
    return response.data;
  },
};

/**
 * Events API
 */
export const eventsApi = {
  /**
   * Log a single user interaction event.
   *
   * @param event - Event data to log
   * @returns Promise with logged event response
   *
   * @example
   * const response = await eventsApi.logEvent({
   *   user_id: 'user_123',
   *   item_id: 'item_456',
   *   event_type: 'click'
   * });
   */
  async logEvent(event: EventCreate): Promise<EventResponse> {
    const response = await apiClient.post<EventResponse>('/event', event);
    return response.data;
  },

  /**
   * Log multiple events in a batch.
   *
   * @param events - Array of events to log
   * @returns Promise with array of logged event responses
   *
   * @example
   * const responses = await eventsApi.logEventsBatch([
   *   { user_id: 'user_1', item_id: 'item_1', event_type: 'view' },
   *   { user_id: 'user_1', item_id: 'item_2', event_type: 'click' }
   * ]);
   */
  async logEventsBatch(events: EventCreate[]): Promise<EventResponse[]> {
    const response = await apiClient.post<EventResponse[]>('/events/batch', events);
    return response.data;
  },
};

/**
 * Metrics API
 */
export const metricsApi = {
  /**
   * Get comprehensive system metrics.
   *
   * @returns Promise with metrics response
   *
   * @example
   * const metrics = await metricsApi.getMetrics();
   * console.log(metrics.prediction_metrics.total_predictions);
   */
  async getMetrics(): Promise<MetricsResponse> {
    const response = await apiClient.get<MetricsResponse>('/metrics');
    return response.data;
  },

  /**
   * Get Prometheus-formatted metrics.
   *
   * @returns Promise with raw Prometheus metrics text
   */
  async getPrometheusMetrics(): Promise<string> {
    const response = await apiClient.get('/metrics/prometheus', {
      responseType: 'text',
    });
    return response.data;
  },

  /**
   * Get drift detection results.
   *
   * @returns Promise with drift metrics
   *
   * @example
   * const drift = await metricsApi.getDriftMetrics();
   * console.log(drift.status, drift.feature_drift_score);
   */
  async getDriftMetrics(): Promise<{
    feature_drift_score: number;
    prediction_drift_score: number;
    status: string;
    drifted_features: string[];
  }> {
    const response = await apiClient.get('/metrics/drift');
    return response.data;
  },

  /**
   * Get metrics summary.
   *
   * @returns Promise with metrics summary
   *
   * @example
   * const summary = await metricsApi.getSummary();
   * console.log(summary.predictions_total, summary.average_latency_ms);
   */
  async getSummary(): Promise<MetricsSummary> {
    const response = await apiClient.get<MetricsSummary>('/metrics/summary');
    return response.data;
  },

  /**
   * Get dashboard metrics for visualization.
   *
   * @returns Promise with comprehensive dashboard metrics
   *
   * @example
   * const dashboard = await metricsApi.getDashboardMetrics();
   * console.log(dashboard.events.total, dashboard.model.rmse);
   */
  async getDashboardMetrics(): Promise<{
    events: {
      total: number;
      by_type: Record<string, number>;
      last_hour: number;
      per_minute: number;
    };
    recommendations: {
      total: number;
      last_hour: number;
      average_latency_ms: number;
      p95_latency_ms: number;
      cache_hit_rate: number;
    };
    learning: {
      user_embeddings_updated: number;
      item_embeddings_updated: number;
      total_users: number;
      total_items: number;
      cache_hit_rate: number;
    };
    model: {
      version: string;
      loaded: boolean;
      rmse: number;
      r2_score: number;
      map_at_10: number;
      last_trained: string;
    };
    system: {
      uptime_seconds: number;
      timestamp: string;
    };
  }> {
    const response = await apiClient.get('/metrics/dashboard');
    return response.data;
  },

  /**
   * Get model information and metrics.
   *
   * @returns Promise with model info
   *
   * @example
   * const modelInfo = await metricsApi.getModelInfo();
   * console.log(modelInfo.metrics.rmse, modelInfo.training.date);
   */
  async getModelInfo(): Promise<{
    version: string;
    loaded: boolean;
    metrics: {
      rmse: number;
      mae: number;
      r2: number;
      'recall@5': number;
      'recall@10': number;
      'map@5': number;
      'map@10': number;
    };
    training: {
      date: string;
      dataset_size: number;
      n_users: number;
      n_items: number;
    };
    timestamp: string;
  }> {
    const response = await apiClient.get('/metrics/model-info');
    return response.data;
  },
};

/**
 * Health API
 */
export const healthApi = {
  /**
   * Get comprehensive health check.
   *
   * @returns Promise with health check response
   *
   * @example
   * const health = await healthApi.getHealth();
   * console.log(health.status, health.components);
   */
  async getHealth(): Promise<HealthCheckResponse> {
    const response = await apiClient.get<HealthCheckResponse>('/health');
    return response.data;
  },

  /**
   * Liveness probe - is the service running?
   *
   * @returns Promise with liveness status
   */
  async getLiveness(): Promise<{ status: string; timestamp: string }> {
    const response = await apiClient.get('/health/live');
    return response.data;
  },

  /**
   * Readiness probe - is the service ready to serve?
   *
   * @returns Promise with readiness status
   */
  async getReadiness(): Promise<{ status: string; timestamp: string }> {
    const response = await apiClient.get('/health/ready');
    return response.data;
  },
};

export default {
  recommendation: recommendationApi,
  events: eventsApi,
  metrics: metricsApi,
  health: healthApi,
};
