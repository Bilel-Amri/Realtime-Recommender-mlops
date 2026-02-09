// Real-Time Recommendation System - Health Check Page
import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { healthApi } from '../services/api';

const HealthPage: React.FC = () => {
  const healthQuery = useQuery({
    queryKey: ['health'],
    queryFn: () => healthApi.getHealth(),
    refetchInterval: 15000,
  });

  if (healthQuery.isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 'var(--spacing-2xl)' }} className="fade-in">
        <div className="loading" style={{
          height: '200px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1.1rem'
        }}>
          Loading health status...
        </div>
      </div>
    );
  }

  if (healthQuery.isError) {
    return (
      <div className="card fade-in" style={{ textAlign: 'center', padding: 'var(--spacing-2xl)' }}>
        <div style={{ fontSize: '3rem', marginBottom: 'var(--spacing-md)' }}>⚠️</div>
        <div style={{ color: 'var(--color-error)', fontSize: '1.1rem' }}>
          Failed to load health status
        </div>
      </div>
    );
  }

  const health = healthQuery.data;

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'healthy':
        return 'var(--color-success)';
      case 'degraded':
        return 'var(--color-warning)';
      default:
        return 'var(--color-error)';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'healthy':
        return '✓';
      case 'degraded':
        return '⚠';
      default:
        return '✕';
    }
  };

  const formatUptime = (seconds: number): string => {
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
    if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}h`;
    return `${(seconds / 86400).toFixed(1)}d`;
  };

  return (
    <div style={{ maxWidth: '1400px', margin: '0 auto' }} className="fade-in">
      {/* Hero Status Banner */}
      <div className="card" style={{
        marginBottom: 'var(--spacing-xl)',
        background: `linear-gradient(135deg, ${getStatusColor(health?.status || 'unknown')}15 0%, ${getStatusColor(health?.status || 'unknown')}05 100%)`,
        border: `1px solid ${getStatusColor(health?.status || 'unknown')}40`
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--spacing-xl)'
        }}>
          <div style={{
            width: '80px',
            height: '80px',
            borderRadius: '50%',
            background: `linear-gradient(135deg, ${getStatusColor(health?.status || 'unknown')} 0%, ${getStatusColor(health?.status || 'unknown')}CC 100%)`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '2.5rem',
            color: 'white',
            boxShadow: `0 0 30px ${getStatusColor(health?.status || 'unknown')}60`
          }}>
            {getStatusIcon(health?.status || 'unknown')}
          </div>
          <div style={{ flex: 1 }}>
            <h1 style={{
              fontSize: '2rem',
              fontWeight: 800,
              marginBottom: 'var(--spacing-xs)',
              color: 'var(--text-primary)'
            }}>
              Service {health?.status === 'healthy' ? 'Healthy' : health?.status === 'degraded' ? 'Degraded' : 'Unhealthy'}
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>
              Last checked: {health && new Date(health.timestamp).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Key Metrics */}
      <div className="card" style={{ marginBottom: 'var(--spacing-xl)' }}>
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: 700,
          marginBottom: 'var(--spacing-lg)',
          color: 'var(--text-primary)'
        }}>
          Key Metrics
        </h2>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--spacing-md)'
        }}>
          <div style={{
            padding: 'var(--spacing-lg)',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-color)'
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              Version
            </div>
            <div style={{
              fontSize: '2rem',
              fontWeight: 'bold',
              color: 'var(--text-primary)'
            }}>
              {health?.version}
            </div>
          </div>
          <div style={{
            padding: 'var(--spacing-lg)',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-color)'
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              Uptime
            </div>
            <div style={{
              fontSize: '2rem',
              fontWeight: 'bold',
              background: 'var(--gradient-success)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              {health && formatUptime(health.uptime_seconds)}
            </div>
          </div>
          <div style={{
            padding: 'var(--spacing-lg)',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-color)'
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              Components
            </div>
            <div style={{
              fontSize: '2rem',
              fontWeight: 'bold',
              color: 'var(--text-primary)'
            }}>
              {health?.components.length}
            </div>
          </div>
          <div style={{
            padding: 'var(--spacing-lg)',
            background: 'var(--bg-secondary)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-color)'
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
              Healthy Components
            </div>
            <div style={{
              fontSize: '2rem',
              fontWeight: 'bold',
              background: 'var(--gradient-success)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text'
            }}>
              {health?.components.filter((c) => c.status === 'healthy').length}
            </div>
          </div>
        </div>
      </div>

      {/* Component Status */}
      <div className="card">
        <h2 style={{
          fontSize: '1.5rem',
          fontWeight: 700,
          marginBottom: 'var(--spacing-lg)',
          color: 'var(--text-primary)'
        }}>
          Component Status
        </h2>
        <div style={{ display: 'grid', gap: 'var(--spacing-md)' }}>
          {health?.components.map((component) => (
            <div
              key={component.name}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: 'var(--spacing-lg)',
                background: 'var(--bg-secondary)',
                borderRadius: 'var(--radius-lg)',
                border: `1px solid ${getStatusColor(component.status)}40`,
                borderLeft: `4px solid ${getStatusColor(component.status)}`,
                transition: 'all var(--transition-base)'
              }}
            >
              <div style={{
                width: '48px',
                height: '48px',
                borderRadius: '50%',
                background: `${getStatusColor(component.status)}20`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '1.5rem',
                marginRight: 'var(--spacing-lg)',
                color: getStatusColor(component.status)
              }}>
                {getStatusIcon(component.status)}
              </div>
              <div style={{ flex: 1 }}>
                <div style={{
                  fontWeight: 600,
                  fontSize: '1.1rem',
                  color: 'var(--text-primary)',
                  marginBottom: '0.25rem'
                }}>
                  {component.name}
                </div>
                <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                  Status: <span style={{ color: getStatusColor(component.status), fontWeight: 600 }}>
                    {component.status}
                  </span>
                  {component.message && ` - ${component.message}`}
                </div>
              </div>
              {component.latency_ms && (
                <div style={{
                  padding: 'var(--spacing-sm) var(--spacing-md)',
                  background: 'var(--bg-tertiary)',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.875rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)'
                }}>
                  {component.latency_ms.toFixed(2)}ms
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default HealthPage;
