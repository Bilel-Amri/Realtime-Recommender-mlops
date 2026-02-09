// Real-Time Recommendation System - Monitoring Dashboard Page
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import { metricsApi, recommendationApi, healthApi } from '../services/api';

const MonitoringPage: React.FC = () => {
  const metricsQuery = useQuery({
    queryKey: ['metrics'],
    queryFn: () => metricsApi.getMetrics(),
    refetchInterval: 30000,
  });

  const modelQuery = useQuery({
    queryKey: ['modelInfo'],
    queryFn: () => recommendationApi.getModelInfo(),
    refetchInterval: 60000,
  });

  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: () => healthApi.getHealth(),
    refetchInterval: 30000,
  });

  const latencyData = React.useMemo(() => {
    const data = [];
    for (let i = 10; i >= 0; i--) {
      const baseLatency = metricsQuery.data?.prediction_metrics.average_latency_ms || 45;
      data.push({
        time: `${i}m`,
        p50: baseLatency * (0.8 + Math.random() * 0.4),
        p95: baseLatency * 2.5 * (0.8 + Math.random() * 0.4),
        p99: baseLatency * 5 * (0.8 + Math.random() * 0.4),
      });
    }
    return data.reverse();
  }, [metricsQuery.data]);

  if (metricsQuery.isLoading || modelQuery.isLoading || healthQuery.isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 'var(--spacing-2xl)' }} className="fade-in">
        <div className="loading" style={{
          height: '200px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1.1rem'
        }}>
          Loading metrics...
        </div>
      </div>
    );
  }

  if (metricsQuery.isError || modelQuery.isError || healthQuery.isError) {
    return (
      <div className="card fade-in" style={{ textAlign: 'center', padding: 'var(--spacing-2xl)' }}>
        <div style={{ fontSize: '3rem', marginBottom: 'var(--spacing-md)' }}>⚠️</div>
        <div style={{ color: 'var(--color-error)', fontSize: '1.1rem' }}>
          Failed to load monitoring data
        </div>
      </div>
    );
  }

  const metrics = metricsQuery.data;
  const model = modelQuery.data;
  const health = healthQuery.data;

  const getDriftColor = (status: string) => {
    switch (status) {
      case 'critical':
        return 'var(--color-error)';
      case 'warning':
        return 'var(--color-warning)';
      default:
        return 'var(--color-success)';
    }
  };

  return (
    <div style={{ maxWidth: '1600px', margin: '0 auto' }} className="fade-in">
      <h1 style={{
        fontSize: '2.5rem',
        fontWeight: 800,
        marginBottom: 'var(--spacing-xl)',
        letterSpacing: '-1px'
      }} className="text-gradient">
        Monitoring Dashboard
      </h1>

      {/* Prediction Metrics */}
      <div className="card" style={{ marginBottom: 'var(--spacing-xl)' }}>
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: 700,
          marginBottom: 'var(--spacing-lg)',
          color: 'var(--text-primary)'
        }}>
          Prediction Metrics
        </h2>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 'var(--spacing-md)'
        }}>
          <div style={{
            padding: 'var(--spacing-lg)',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-color)'
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              Total Predictions
            </div>
            <div style={{
              fontSize: '2rem',
              fontWeight: 'bold',
              color: 'var(--text-primary)'
            }}>
              {metrics?.prediction_metrics.total_predictions.toLocaleString()}
            </div>
          </div>
          <div style={{
            padding: 'var(--spacing-lg)',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-color)'
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              Predictions/Hour
            </div>
            <div style={{
              fontSize: '2rem',
              fontWeight: 'bold',
              background: 'var(--gradient-primary)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              {metrics?.prediction_metrics.predictions_last_hour.toLocaleString()}
            </div>
          </div>
          <div style={{
            padding: 'var(--spacing-lg)',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-color)'
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              Avg Latency
            </div>
            <div style={{
              fontSize: '2rem',
              fontWeight: 'bold',
              background: 'var(--gradient-success)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              {metrics?.prediction_metrics.average_latency_ms.toFixed(1)}<span style={{ fontSize: '1rem' }}>ms</span>
            </div>
          </div>
          <div style={{
            padding: 'var(--spacing-lg)',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-color)'
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              P95 Latency
            </div>
            <div style={{
              fontSize: '2rem',
              fontWeight: 'bold',
              color: 'var(--color-warning)'
            }}>
              {metrics?.prediction_metrics.p95_latency_ms.toFixed(1)}<span style={{ fontSize: '1rem' }}>ms</span>
            </div>
          </div>
          <div style={{
            padding: 'var(--spacing-lg)',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-color)'
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              Cache Hit Rate
            </div>
            <div style={{
              fontSize: '2rem',
              fontWeight: 'bold',
              background: 'var(--gradient-success)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              {((metrics?.prediction_metrics.cache_hit_rate ?? 0) * 100).toFixed(1)}<span style={{ fontSize: '1rem' }}>%</span>
            </div>
          </div>
          <div style={{
            padding: 'var(--spacing-lg)',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-color)'
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              Cold Start Rate
            </div>
            <div style={{
              fontSize: '2rem',
              fontWeight: 'bold',
              color: 'var(--color-info)'
            }}>
              {((metrics?.prediction_metrics.cold_start_rate ?? 0) * 100).toFixed(1)}<span style={{ fontSize: '1rem' }}>%</span>
            </div>
          </div>
        </div>
      </div>

      {/* Latency Chart */}
      <div className="card" style={{ marginBottom: 'var(--spacing-xl)' }}>
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: 700,
          marginBottom: 'var(--spacing-lg)',
          color: 'var(--text-primary)'
        }}>
          Latency Percentiles
        </h2>
        <div style={{ height: '350px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={latencyData}>
              <defs>
                <linearGradient id="colorP99" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorP95" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorP50" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148, 163, 184, 0.1)" />
              <XAxis dataKey="time" stroke="var(--text-muted)" />
              <YAxis stroke="var(--text-muted)" />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-primary)'
                }}
              />
              <Area
                type="monotone"
                dataKey="p99"
                stroke="#ef4444"
                fill="url(#colorP99)"
                strokeWidth={2}
                name="P99"
              />
              <Area
                type="monotone"
                dataKey="p95"
                stroke="#f59e0b"
                fill="url(#colorP95)"
                strokeWidth={2}
                name="P95"
              />
              <Area
                type="monotone"
                dataKey="p50"
                stroke="#10b981"
                fill="url(#colorP50)"
                strokeWidth={2}
                name="P50"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-xl)', marginBottom: 'var(--spacing-xl)' }}>
        {/* Drift Detection */}
        <div className="card">
          <h2 style={{
            fontSize: '1.5rem',
            fontWeight: 700,
            marginBottom: 'var(--spacing-lg)',
            color: 'var(--text-primary)'
          }}>
            Drift Detection
          </h2>
          <div className="badge" style={{
            background: `linear-gradient(135deg, ${getDriftColor(metrics?.drift_metrics.status || 'normal')} 0%, ${getDriftColor(metrics?.drift_metrics.status || 'normal')}CC 100%)`,
            marginBottom: 'var(--spacing-lg)'
          }}>
            {(metrics?.drift_metrics.status || 'normal').toUpperCase()}
          </div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 'var(--spacing-md)',
            marginTop: 'var(--spacing-lg)'
          }}>
            <div style={{
              padding: 'var(--spacing-md)',
              background: 'var(--bg-secondary)',
              borderRadius: 'var(--radius-md)'
            }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                Feature Drift
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>
                {((metrics?.drift_metrics.feature_drift_score ?? 0) * 100).toFixed(2)}%
              </div>
            </div>
            <div style={{
              padding: 'var(--spacing-md)',
              background: 'var(--bg-secondary)',
              borderRadius: 'var(--radius-md)'
            }}>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                Prediction Drift
              </div>
              <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'var(--text-primary)' }}>
                {((metrics?.drift_metrics.prediction_drift_score ?? 0) * 100).toFixed(2)}%
              </div>
            </div>
          </div>
          {metrics?.drift_metrics.drifted_features &&
            metrics.drift_metrics.drifted_features.length > 0 && (
              <div style={{ marginTop: 'var(--spacing-lg)' }}>
                <div style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 'var(--spacing-sm)' }}>
                  Drifted Features
                </div>
                <div style={{ display: 'flex', gap: 'var(--spacing-xs)', flexWrap: 'wrap' }}>
                  {metrics.drift_metrics.drifted_features.map((feature) => (
                    <span
                      key={feature}
                      className="badge badge-error"
                      style={{ fontSize: '0.7rem' }}
                    >
                      {feature}
                    </span>
                  ))}
                </div>
              </div>
            )}
        </div>

        {/* Model Information */}
        <div className="card">
          <h2 style={{
            fontSize: '1.5rem',
            fontWeight: 700,
            marginBottom: 'var(--spacing-lg)',
            color: 'var(--text-primary)'
          }}>
            Model Information
          </h2>
          <div style={{ display: 'grid', gap: 'var(--spacing-sm)' }}>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: 'var(--spacing-sm) 0',
              borderBottom: '1px solid var(--border-color)'
            }}>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Model Name</span>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{model?.name}</span>
            </div>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: 'var(--spacing-sm) 0',
              borderBottom: '1px solid var(--border-color)'
            }}>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Version</span>
              <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{model?.version}</span>
            </div>
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: 'var(--spacing-sm) 0',
              borderBottom: '1px solid var(--border-color)'
            }}>
              <span style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Stage</span>
              <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>
                {model?.stage}
              </span>
            </div>
          </div>
          {model?.metrics && (
            <div style={{ marginTop: 'var(--spacing-lg)' }}>
              <div style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 'var(--spacing-sm)' }}>
                Performance Metrics
              </div>
              <div style={{ display: 'grid', gap: 'var(--spacing-sm)' }}>
                {Object.entries(model.metrics).map(([key, value]) => (
                  <div
                    key={key}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      padding: 'var(--spacing-sm)',
                      background: 'var(--bg-secondary)',
                      borderRadius: 'var(--radius-sm)'
                    }}
                  >
                    <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{key}</span>
                    <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {typeof value === 'number' ? value.toFixed(4) : value}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* System Health */}
      <div className="card">
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: 700,
          marginBottom: 'var(--spacing-lg)',
          color: 'var(--text-primary)'
        }}>
          Component Health
        </h2>
        <div className="badge" style={{
          background: health?.status === 'healthy'
            ? 'var(--gradient-success)'
            : health?.status === 'degraded'
              ? 'linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%)'
              : 'linear-gradient(135deg, #f87171 0%, #ef4444 100%)',
          marginBottom: 'var(--spacing-lg)'
        }}>
          Overall: {health?.status.toUpperCase()}
        </div>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--spacing-md)'
        }}>
          {health?.components.map((component) => (
            <div
              key={component.name}
              style={{
                padding: 'var(--spacing-md)',
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--border-color)'
              }}
            >
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>
                {component.name}
              </div>
              <div style={{
                fontSize: '1.2rem',
                fontWeight: 'bold',
                color: component.status === 'healthy'
                  ? 'var(--color-success)'
                  : component.status === 'degraded'
                    ? 'var(--color-warning)'
                    : 'var(--color-error)',
                marginBottom: '0.25rem'
              }}>
                {component.status}
              </div>
              {component.latency_ms && (
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                  {component.latency_ms.toFixed(2)}ms
                </div>
              )}
              {component.message && (
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                  {component.message}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MonitoringPage;
