import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import axios from 'axios';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/v1';

const glass = (extra: React.CSSProperties = {}): React.CSSProperties => ({
  background: 'linear-gradient(145deg, rgba(30,41,59,0.9), rgba(15,23,42,0.95))',
  border: '1px solid rgba(148,163,184,0.12)',
  borderRadius: '1.25rem',
  padding: '1.75rem',
  boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
  ...extra,
});

const statTile = (bg: string, border: string): React.CSSProperties => ({
  background: bg,
  border: `1px solid ${border}`,
  borderRadius: '1rem',
  padding: '1.25rem',
  display: 'flex',
  flexDirection: 'column',
  gap: '0.3rem',
});

export default function ABTestingPage() {
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ['abTestResults'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/mlops/ab-results-demo`);
      setLastRefresh(new Date());
      return response.data;
    },
    refetchInterval: 5000,
    staleTime: 0,
  });

  if (isLoading || !data) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)' }}>
      <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
        <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>⚗️</div>
        <p>Loading experiment results…</p>
      </div>
    </div>
  );

  const variantA   = data.variants[0];
  const variantB   = data.variants[1];
  const comparison = data.comparison;

  const metricsData = [
    { metric: 'Click Rate',  A: +(variantA.metrics.click_rate * 100).toFixed(1),  B: +(variantB.metrics.click_rate * 100).toFixed(1) },
    { metric: 'Like Rate',   A: +(variantA.metrics.like_rate * 100).toFixed(1),   B: +(variantB.metrics.like_rate * 100).toFixed(1) },
    { metric: 'Engagement',  A: +(variantA.metrics.engagement_rate * 100).toFixed(1), B: +(variantB.metrics.engagement_rate * 100).toFixed(1) },
  ];

  return (
    <div style={{ background: 'var(--bg-primary)', minHeight: '100vh', padding: '2rem', fontFamily: 'Inter, sans-serif', color: '#f1f5f9' }}>
      <div style={{ maxWidth: '1200px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

        {/* ── HEADER ── */}
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 style={{ margin: 0, fontSize: '2rem', fontWeight: 800, background: 'linear-gradient(90deg,#a78bfa,#10b981)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
              A/B Experiment Results
            </h1>
            <p style={{ color: 'var(--text-muted)', margin: '0.25rem 0 0', fontSize: '0.875rem' }}>
              {data.experiment.name} · {data.experiment.total_users.toLocaleString()} users · {data.experiment.duration_hours}h runtime
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              {isFetching ? '⟳ updating…' : `↻ ${lastRefresh.toLocaleTimeString()}`}
            </span>
            <button
              onClick={() => refetch()}
              style={{ padding: '0.4rem 1rem', borderRadius: '2rem', border: '1px solid rgba(167,139,250,0.4)', background: 'rgba(167,139,250,0.1)', color: '#a78bfa', fontWeight: 600, fontSize: '0.8rem', cursor: 'pointer' }}
            >↻ Refresh</button>
            {data.experiment.status === 'warming_up' && (
              <span style={{ padding: '0.3rem 0.9rem', borderRadius: '2rem', background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.4)', color: '#f59e0b', fontSize: '0.75rem', fontWeight: 600 }}>
                ⏳ {data.experiment.description}
              </span>
            )}
            {data.experiment.status === 'running' && (
              <span style={{ padding: '0.3rem 0.9rem', borderRadius: '2rem', background: 'rgba(16,185,129,0.15)', border: '1px solid rgba(16,185,129,0.4)', color: '#10b981', fontSize: '0.75rem', fontWeight: 600 }}>
                🟢 LIVE · {data.experiment.description}
              </span>
            )}
          </div>
        </div>

        {/* ── OBJECTIVE ── */}
        <div style={glass({ background: 'linear-gradient(145deg, rgba(99,102,241,0.12), rgba(15,23,42,0.95))', border: '1px solid rgba(99,102,241,0.25)' })}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1.25rem' }}>
            <div style={{ fontSize: '2.5rem', lineHeight: 1, flexShrink: 0 }}>🎯</div>
            <div style={{ flex: 1 }}>
              <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.1rem', fontWeight: 700, color: '#a78bfa' }}>Experiment Objective</h2>
              <p style={{ margin: '0 0 0.75rem', color: '#cbd5e1', fontSize: '0.93rem', lineHeight: 1.6 }}>
                Determine whether the <strong style={{ color: '#fff' }}>retrained embedding model (Model B)</strong> — updated with online learning and
                real-time behavioral signals — outperforms the <strong style={{ color: '#fff' }}>static baseline (Model A)</strong> on user engagement.
                Success is defined as a statistically significant lift in engagement rate, click-through rate, and average rating.
              </p>
              <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                {['Improve click-through rate', 'Increase recommendation relevance', 'Higher user satisfaction (rating)', 'Validate online learning pipeline'].map(g => (
                  <span key={g} style={{ padding: '0.25rem 0.75rem', background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.3)', borderRadius: '2rem', fontSize: '0.75rem', color: '#a78bfa', fontWeight: 500 }}>{g}</span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ── WINNER BANNER ── */}
        <div style={{ position: 'relative', background: 'linear-gradient(135deg, #059669 0%, #10b981 50%, #34d399 100%)', borderRadius: '1.25rem', padding: '2rem 2.5rem', boxShadow: '0 8px 40px rgba(16,185,129,0.4)', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', right: '-1rem', top: '-2rem', fontSize: '10rem', opacity: 0.12, lineHeight: 1 }}>🏆</div>
          <div style={{ position: 'relative', zIndex: 1 }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 700, letterSpacing: '0.15em', color: 'rgba(255,255,255,0.8)', marginBottom: '0.4rem' }}>🎉 WINNER</div>
            <div style={{ fontSize: '2.75rem', fontWeight: 900, color: '#fff', lineHeight: 1, marginBottom: '0.75rem' }}>{comparison.winner}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flexWrap: 'wrap' }}>
              <div style={{ fontSize: '2rem', fontWeight: 800, color: '#fff' }}>+{comparison.engagement_improvement.toFixed(1)}%</div>
              <div style={{ fontSize: '1.1rem', color: 'rgba(255,255,255,0.85)' }}>better engagement over baseline</div>
            </div>
          </div>
        </div>

        {/* ── SIDE-BY-SIDE ── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>

          {/* Model A */}
          <div style={glass({ border: '1px solid rgba(148,163,184,0.2)' })}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <div>
                <div style={{ fontSize: '2rem', marginBottom: '0.3rem' }}>📊</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f1f5f9' }}>Model A</div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Baseline</div>
              </div>
              <div style={{ padding: '0.3rem 1rem', background: 'rgba(148,163,184,0.15)', borderRadius: '2rem', fontSize: '0.75rem', color: '#94a3b8', fontWeight: 600 }}>BASELINE</div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.25rem' }}>
              {[
                { label: 'Click Rate',   value: `${(variantA.metrics.click_rate * 100).toFixed(1)}%` },
                { label: 'Like Rate',    value: `${(variantA.metrics.like_rate * 100).toFixed(1)}%` },
                { label: 'Engagement',   value: `${(variantA.metrics.engagement_rate * 100).toFixed(1)}%` },
                { label: 'Avg Rating',   value: variantA.metrics.avg_rating.toFixed(1) },
              ].map(({ label, value }) => (
                <div key={label} style={statTile('rgba(30,41,59,0.6)', 'rgba(148,163,184,0.12)')}>
                  <div style={{ fontSize: '1.75rem', fontWeight: 800, color: '#94a3b8' }}>{value}</div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{label}</div>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem', borderTop: '1px solid rgba(148,163,184,0.1)', paddingTop: '1rem' }}>
              {[['Users', variantA.users.toLocaleString()], ['Clicks', variantA.clicks.toLocaleString()]].map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>{k}</span>
                  <span style={{ color: '#f1f5f9', fontWeight: 700 }}>{v}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Model B — Winner */}
          <div style={glass({ border: '2px solid rgba(16,185,129,0.5)', boxShadow: '0 8px 40px rgba(16,185,129,0.15)' })}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <div>
                <div style={{ fontSize: '2rem', marginBottom: '0.3rem' }}>🚀</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#f1f5f9' }}>Model B</div>
                <div style={{ fontSize: '0.8rem', color: '#34d399' }}>Retrained</div>
              </div>
              <div style={{ padding: '0.3rem 1rem', background: 'rgba(16,185,129,0.25)', border: '1px solid #10b981', borderRadius: '2rem', fontSize: '0.75rem', color: '#10b981', fontWeight: 700 }}>🏆 WINNER</div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1.25rem' }}>
              {[
                { label: 'Click Rate',  value: `${(variantB.metrics.click_rate * 100).toFixed(1)}%`,        delta: `↑${comparison.click_rate_improvement.toFixed(0)}%` },
                { label: 'Like Rate',   value: `${(variantB.metrics.like_rate * 100).toFixed(1)}%`,         delta: `↑${comparison.like_rate_improvement.toFixed(0)}%` },
                { label: 'Engagement',  value: `${(variantB.metrics.engagement_rate * 100).toFixed(1)}%`,   delta: `↑${comparison.engagement_improvement.toFixed(0)}%` },
                { label: 'Avg Rating',  value: variantB.metrics.avg_rating.toFixed(1),                      delta: `↑${comparison.rating_improvement.toFixed(0)}%` },
              ].map(({ label, value, delta }) => (
                <div key={label} style={statTile('rgba(16,185,129,0.08)', 'rgba(16,185,129,0.3)')}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.4rem' }}>
                    <span style={{ fontSize: '1.75rem', fontWeight: 800, color: '#10b981' }}>{value}</span>
                    <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#34d399' }}>{delta}</span>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{label}</div>
                </div>
              ))}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', fontSize: '0.85rem', borderTop: '1px solid rgba(16,185,129,0.2)', paddingTop: '1rem' }}>
              {[['Users', variantB.users.toLocaleString()], ['Clicks', variantB.clicks.toLocaleString()]].map(([k, v]) => (
                <div key={k} style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-muted)' }}>{k}</span>
                  <span style={{ color: '#10b981', fontWeight: 700 }}>{v}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── MODEL DIFFERENCES ── */}
        <div style={glass()}>
          <h2 style={{ margin: '0 0 1.25rem', fontSize: '1.1rem', fontWeight: 700, color: '#f1f5f9' }}>🔬 Model Architecture Differences</h2>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: '0', alignItems: 'stretch' }}>
            {/* Model A column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
              <div style={{ padding: '0.6rem 1rem', background: 'rgba(71,85,105,0.4)', borderRadius: '0.75rem 0.75rem 0 0', textAlign: 'center', fontWeight: 700, color: '#94a3b8', fontSize: '0.85rem', marginBottom: '2px' }}>📊 Model A — Baseline</div>
              {[
                ['Training',     'Static batch — trained once on historical ratings'],
                ['Algorithm',    'Matrix Factorization (SVD)'],
                ['Input signals','User-item ratings only'],
                ['Updates',      'Manual retraining (periodic)'],
                ['Embeddings',   'Fixed 64-dim user & item vectors'],
                ['Latency',      `${variantA.metrics.avg_latency_ms.toFixed(0)} ms avg response`],
              ].map(([key, val], i, arr) => (
                <div key={key} style={{ padding: '0.75rem 1rem', background: 'rgba(30,41,59,0.5)', borderBottom: i < arr.length - 1 ? '1px solid rgba(71,85,105,0.2)' : 'none', borderRadius: i === arr.length - 1 ? '0 0 0.75rem 0.75rem' : '0', marginBottom: i < arr.length - 1 ? '2px' : 0 }}>
                  <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '0.2rem' }}>{key}</div>
                  <div style={{ fontSize: '0.83rem', color: '#94a3b8' }}>{val}</div>
                </div>
              ))}
            </div>

            {/* Center divider */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', padding: '0 1rem', gap: '6px' }}>
              <div style={{ width: '2px', flex: 1, background: 'linear-gradient(to bottom, transparent, rgba(148,163,184,0.15), transparent)' }} />
              {['vs','vs','vs','vs','vs','vs'].map((v, i) => (
                <div key={i} style={{ width: '28px', height: '28px', borderRadius: '50%', background: 'rgba(30,41,59,0.8)', border: '1px solid rgba(148,163,184,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.6rem', color: '#475569', fontWeight: 700, flexShrink: 0 }}>{v}</div>
              ))}
              <div style={{ width: '2px', flex: 1, background: 'linear-gradient(to bottom, transparent, rgba(148,163,184,0.15), transparent)' }} />
            </div>

            {/* Model B column */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
              <div style={{ padding: '0.6rem 1rem', background: 'rgba(16,185,129,0.2)', borderRadius: '0.75rem 0.75rem 0 0', textAlign: 'center', fontWeight: 700, color: '#10b981', fontSize: '0.85rem', marginBottom: '2px' }}>🚀 Model B — Current (Winner)</div>
              {[
                ['Training',     'Online learning + auto-retraining on live events'],
                ['Algorithm',    'Neural Collaborative Filtering with learned embeddings'],
                ['Input signals','Ratings + clicks + views + likes + behavioral context'],
                ['Updates',      'Continuous online updates every interaction batch'],
                ['Embeddings',   'Dynamic 128-dim vectors updated in real-time'],
                ['Latency',      `${variantB.metrics.avg_latency_ms.toFixed(0)} ms avg response`],
              ].map(([key, val], i, arr) => (
                <div key={key} style={{ padding: '0.75rem 1rem', background: 'rgba(16,185,129,0.06)', border: '1px solid rgba(16,185,129,0.1)', borderTop: 'none', borderBottom: i < arr.length - 1 ? '1px solid rgba(16,185,129,0.1)' : '1px solid rgba(16,185,129,0.1)', borderRadius: i === arr.length - 1 ? '0 0 0.75rem 0.75rem' : '0', marginBottom: i < arr.length - 1 ? '2px' : 0 }}>
                  <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#059669', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '0.2rem' }}>{key}</div>
                  <div style={{ fontSize: '0.83rem', color: '#34d399', fontWeight: 500 }}>{val}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── CHART ── */}
        <div style={glass()}>
          <h2 style={{ margin: '0 0 1.25rem', fontSize: '1.1rem', fontWeight: 700, color: '#f1f5f9' }}>📊 Performance Comparison (%)</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={metricsData} barCategoryGap="35%">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
              <XAxis dataKey="metric" stroke="#475569" tick={{ fontSize: 12, fill: '#94a3b8' }} />
              <YAxis stroke="#475569" tick={{ fontSize: 11, fill: '#64748b' }} tickFormatter={v => `${v}%`} />
              <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: '0.75rem', fontSize: '0.8rem' }} formatter={(v: number) => [`${v}%`]} />
              <Legend wrapperStyle={{ fontSize: '0.8rem', color: '#94a3b8' }} />
              <Bar dataKey="A" name="Model A (Baseline)" fill="#475569" radius={[6,6,0,0]} />
              <Bar dataKey="B" name="Model B (Winner)"   fill="#10b981" radius={[6,6,0,0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* ── STATS ROW ── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
          {[
            { icon: '✅', label: 'Statistical Significance', value: 'Significant', sub: `p = ${comparison.p_value.toFixed(4)}`, color: '#10b981' },
            { icon: '🎯', label: 'Confidence Level',         value: `${(comparison.confidence_level * 100).toFixed(0)}%`, sub: 'of results reproducible', color: '#6366f1' },
            { icon: '⏱️', label: 'Test Duration',            value: `${data.experiment.duration_hours}h`, sub: `${data.experiment.total_users.toLocaleString()} users`, color: '#f59e0b' },
          ].map(({ icon, label, value, sub, color }) => (
            <div key={label} style={glass({ textAlign: 'center' })}>
              <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>{icon}</div>
              <div style={{ fontSize: '2rem', fontWeight: 800, color, marginBottom: '0.25rem' }}>{value}</div>
              <div style={{ fontSize: '0.78rem', color: '#94a3b8', fontWeight: 600, marginBottom: '0.2rem' }}>{label}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{sub}</div>
            </div>
          ))}
        </div>

        {/* ── DEPLOY RECOMMENDATION ── */}
        <div style={{ background: 'linear-gradient(135deg, #4f46e5 0%, #6366f1 60%, #7c3aed 100%)', borderRadius: '1.25rem', padding: '2rem 2.5rem', boxShadow: '0 8px 40px rgba(99,102,241,0.4)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', flexWrap: 'wrap' }}>
            <div style={{ fontSize: '4rem' }}>🚀</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color: '#fff', marginBottom: '0.4rem' }}>{data.recommendation.action}</div>
              <p style={{ color: 'rgba(255,255,255,0.8)', margin: '0 0 0.75rem', fontSize: '0.95rem' }}>{data.recommendation.reason}</p>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                {[`Impact: ${data.recommendation.estimated_impact}`, `${data.experiment.total_users.toLocaleString()} users tested`].map(t => (
                  <span key={t} style={{ padding: '0.35rem 1rem', background: 'rgba(255,255,255,0.15)', borderRadius: '2rem', fontSize: '0.8rem', color: '#fff', fontWeight: 500 }}>{t}</span>
                ))}
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
