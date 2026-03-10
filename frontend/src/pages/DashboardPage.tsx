import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  AreaChart, Area, PieChart, Pie, Cell,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, LineChart, Line, Legend,
} from 'recharts';
import { metricsApi, userApi, eventsApi } from '../services/api';

const DEMO_USERS  = ['alice', 'bob', 'carol', 'dave', 'eve', 'frank'];
const DEMO_ITEMS  = Array.from({ length: 20 }, (_, i) => i + 1);
const DEMO_EVENTS = ['view', 'like', 'dislike', 'click', 'rating'] as const;

async function fireDemoEvent() {
  const user   = DEMO_USERS[Math.floor(Math.random() * DEMO_USERS.length)];
  const item   = DEMO_ITEMS[Math.floor(Math.random() * DEMO_ITEMS.length)];
  const type   = DEMO_EVENTS[Math.floor(Math.random() * DEMO_EVENTS.length)];
  const rating = type === 'rating' ? Math.floor(Math.random() * 5) + 1 : undefined;
  try {
    await eventsApi.logEvent({ user_id: user, item_id: item, event_type: type, rating });
  } catch { /* ignore */ }
}

const PALETTE = ['#6366f1','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4','#ec4899','#84cc16'];

/* ─── tiny helpers ─────────────────────────────────────────────────── */
const card = (extra: React.CSSProperties = {}): React.CSSProperties => ({
  background: 'linear-gradient(145deg, rgba(30,41,59,0.9), rgba(15,23,42,0.95))',
  border: '1px solid rgba(148,163,184,0.12)',
  borderRadius: '1.25rem',
  padding: '1.5rem',
  boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
  backdropFilter: 'blur(12px)',
  ...extra,
});

const kpiCard = (gradient: string): React.CSSProperties => ({
  background: gradient,
  borderRadius: '1.25rem',
  padding: '1.5rem',
  boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
  display: 'flex',
  flexDirection: 'column',
  gap: '0.5rem',
  transition: 'transform 0.2s, box-shadow 0.2s',
  cursor: 'default',
  position: 'relative',
  overflow: 'hidden',
});

const statBox = (color: string): React.CSSProperties => ({
  background: 'rgba(15,23,42,0.6)',
  border: `1px solid ${color}33`,
  borderRadius: '1rem',
  padding: '1.25rem',
  display: 'flex',
  flexDirection: 'column',
  gap: '0.4rem',
  transition: 'border-color 0.2s',
});

export default function DashboardPage() {
  const [liveData, setLiveData] = useState<Array<{ time: string; events: number; recs: number }>>([]);
  const [profileUserId, setProfileUserId] = useState('');
  const [profileInput, setProfileInput]   = useState('');
  const [tick, setTick] = useState(0);
  const [demoMode, setDemoMode] = useState(false);
  const [demoCount, setDemoCount] = useState(0);

  // pulse tick every second for animated elements
  useEffect(() => { const id = setInterval(() => setTick(t => t + 1), 1000); return () => clearInterval(id); }, []);

  // demo mode: fire a random event every 800ms
  useEffect(() => {
    if (!demoMode) return;
    const id = setInterval(async () => {
      await fireDemoEvent();
      setDemoCount(c => c + 1);
    }, 800);
    return () => clearInterval(id);
  }, [demoMode]);

  const { data: metrics } = useQuery({
    queryKey: ['dashboardMetrics'],
    queryFn: metricsApi.getDashboardMetrics,
    refetchInterval: 3000,
  });

  const { data: topInterests } = useQuery({
    queryKey: ['topInterests', profileUserId],
    queryFn: () => userApi.getTopInterests(profileUserId),
    enabled: Boolean(profileUserId),
    refetchInterval: 3000,
    retry: false,
  });

  useEffect(() => {
    if (!metrics) return;
    const now = new Date();
    const t = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
    setLiveData(prev => [...prev, { time: t, events: metrics.events.total, recs: metrics.recommendations.total }].slice(-25));
  }, [metrics]);

  if (!metrics) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-primary)' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: '4rem', marginBottom: '1rem', animation: 'spin 1s linear infinite' }}>⚙️</div>
        <p style={{ color: 'var(--text-muted)' }}>Loading dashboard…</p>
      </div>
    </div>
  );

  const eventTypesData = Object.entries(metrics.events.by_type || {}).map(([name, value]) => ({ name, value }));
  const uptime = metrics.system.uptime_seconds || 0;
  const latency = metrics.recommendations.average_latency_ms || 0;
  const isLive = tick % 2 === 0;

  return (
    <div style={{ background: 'var(--bg-primary)', minHeight: '100vh', padding: '2rem', fontFamily: 'Inter, sans-serif' }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

        {/* ── HEADER ─────────────────────────────────────────────────── */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 style={{ fontSize: '2.25rem', fontWeight: 800, margin: 0, background: 'linear-gradient(90deg, #6366f1, #ec4899, #06b6d4)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
              AI Recommendation Monitor
            </h1>
            <p style={{ color: 'var(--text-muted)', margin: '0.25rem 0 0', fontSize: '0.875rem' }}>
              Real-time MLOps Dashboard · MovieLens-100k · ALS + Cosine Similarity
            </p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              onClick={() => setDemoMode(d => !d)}
              style={{
                padding: '0.5rem 1.25rem',
                borderRadius: '2rem',
                border: `1.5px solid ${demoMode ? '#f59e0b' : 'rgba(255,255,255,0.2)'}`,
                background: demoMode ? 'rgba(245,158,11,0.2)' : 'rgba(255,255,255,0.05)',
                color: demoMode ? '#f59e0b' : '#94a3b8',
                fontWeight: 700,
                fontSize: '0.85rem',
                cursor: 'pointer',
                transition: 'all 0.3s',
                display: 'flex',
                alignItems: 'center',
                gap: '0.4rem',
              }}
            >
              <span style={{ fontSize: '1rem' }}>{demoMode ? '⏹' : '▶'}</span>
              {demoMode ? `Demo ON · ${demoCount} events` : 'Demo Mode'}
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', background: isLive ? 'rgba(16,185,129,0.15)' : 'rgba(16,185,129,0.08)', border: '1.5px solid rgba(16,185,129,0.5)', borderRadius: '2rem', padding: '0.5rem 1.25rem', transition: 'background 0.5s' }}>
              <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#10b981', boxShadow: isLive ? '0 0 12px #10b981' : 'none', transition: 'box-shadow 0.5s' }} />
              <span style={{ color: '#10b981', fontWeight: 700, fontSize: '0.9rem', letterSpacing: '0.05em' }}>LIVE</span>
            </div>
          </div>
        </div>

        {/* ── KPI ROW ────────────────────────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
          {[
            { label: 'Total Events', value: metrics.events.total, sub: `${(metrics.events.per_minute || 0).toFixed(1)}/min`, icon: '⚡', gradient: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)', glow: '#6366f1' },
            { label: 'Recommendations', value: metrics.recommendations.total, sub: `${latency.toFixed(0)} ms avg`, icon: '🎯', gradient: 'linear-gradient(135deg, #10b981 0%, #059669 100%)', glow: '#10b981' },
            { label: 'Last Hour Events', value: metrics.events.last_hour, sub: `${metrics.recommendations.last_hour} recs`, icon: '📊', gradient: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)', glow: '#8b5cf6' },
            { label: 'Uptime', value: `${Math.floor(uptime/3600)}h ${Math.floor((uptime%3600)/60)}m`, sub: `P95: ${(metrics.recommendations.p95_latency_ms||0).toFixed(0)}ms`, icon: '⏱️', gradient: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', glow: '#f59e0b' },
          ].map(({ label, value, sub, icon, gradient, glow }) => (
            <div key={label} style={kpiCard(gradient)}
              onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.transform = 'translateY(-4px)'; (e.currentTarget as HTMLDivElement).style.boxShadow = `0 16px 40px ${glow}55`; }}
              onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.transform = ''; (e.currentTarget as HTMLDivElement).style.boxShadow = '0 8px 32px rgba(0,0,0,0.5)'; }}
            >
              <div style={{ position: 'absolute', top: '-20px', right: '-10px', fontSize: '6rem', opacity: 0.15 }}>{icon}</div>
              <div style={{ fontSize: '1.8rem' }}>{icon}</div>
              <div style={{ fontSize: '2.2rem', fontWeight: 900, color: '#fff', lineHeight: 1 }}>{value}</div>
              <div style={{ fontSize: '0.8rem', color: 'rgba(255,255,255,0.7)', fontWeight: 600 }}>{label}</div>
              <div style={{ fontSize: '0.75rem', color: 'rgba(255,255,255,0.5)' }}>{sub}</div>
            </div>
          ))}
        </div>

        {/* ── CHARTS ROW 1 ───────────────────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '1rem' }}>

          {/* Live activity area chart */}
          <div style={card()}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>📈 Live Activity Stream</h2>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', background: 'rgba(99,102,241,0.15)', padding: '0.2rem 0.6rem', borderRadius: '1rem' }}>auto-refresh 3s</span>
            </div>
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={liveData}>
                <defs>
                  <linearGradient id="gEvents" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#6366f1" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0.05}/>
                  </linearGradient>
                  <linearGradient id="gRecs" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#10b981" stopOpacity={0.8}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.05}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
                <XAxis dataKey="time" stroke="#475569" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis stroke="#475569" tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: '0.75rem', fontSize: '0.8rem' }} />
                <Legend wrapperStyle={{ fontSize: '0.8rem', color: '#94a3b8' }} />
                <Area type="monotone" dataKey="events" name="Events" stroke="#6366f1" strokeWidth={2.5} fill="url(#gEvents)" dot={false} />
                <Area type="monotone" dataKey="recs"   name="Recs"   stroke="#10b981" strokeWidth={2.5} fill="url(#gRecs)"   dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Event type donut */}
          <div style={card({ display: 'flex', flexDirection: 'column' })}>
            <h2 style={{ margin: '0 0 1rem', fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>🍩 Event Breakdown</h2>
            <ResponsiveContainer width="100%" height={170}>
              <PieChart>
                <Pie data={eventTypesData} cx="50%" cy="50%" innerRadius={45} outerRadius={75} paddingAngle={4} dataKey="value" strokeWidth={0}>
                  {eventTypesData.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: '0.75rem', fontSize: '0.8rem' }} />
              </PieChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.5rem' }}>
              {eventTypesData.map((item, i) => (
                <div key={item.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <div style={{ width: '10px', height: '10px', borderRadius: '50%', background: PALETTE[i % PALETTE.length], flexShrink: 0 }} />
                    <span style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{item.name}</span>
                  </div>
                  <span style={{ fontSize: '0.9rem', fontWeight: 700, color: PALETTE[i % PALETTE.length] }}>{item.value}</span>
                </div>
              ))}
              {eventTypesData.length === 0 && <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>No events yet — interact with movies!</p>}
            </div>
          </div>
        </div>

        {/* ── MODEL METRICS ROW ──────────────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '0.75rem' }}>
          {[
            { label: 'RMSE',      value: metrics.model.rmse?.toFixed(3),      icon: '🎯', color: '#10b981' },
            { label: 'R² Score',  value: metrics.model.r2_score?.toFixed(3),  icon: '📐', color: '#6366f1' },
            { label: 'MAP@10',    value: metrics.model.map_at_10?.toFixed(3), icon: '🏆', color: '#f59e0b' },
            { label: 'Cache Hit', value: `${((metrics.recommendations.cache_hit_rate||0)*100).toFixed(0)}%`, icon: '⚡', color: '#06b6d4' },
            { label: 'Users',     value: metrics.learning.total_users || 0,   icon: '👥', color: '#8b5cf6' },
            { label: 'Movies',    value: metrics.learning.total_items || 0,   icon: '🎬', color: '#ec4899' },
          ].map(({ label, value, icon, color }) => (
            <div key={label} style={statBox(color)}
              onMouseEnter={e => { (e.currentTarget as HTMLDivElement).style.borderColor = color + '66'; }}
              onMouseLeave={e => { (e.currentTarget as HTMLDivElement).style.borderColor = color + '33'; }}
            >
              <div style={{ fontSize: '1.5rem' }}>{icon}</div>
              <div style={{ fontSize: '1.5rem', fontWeight: 800, color, lineHeight: 1 }}>{value ?? '—'}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', fontWeight: 500 }}>{label}</div>
            </div>
          ))}
        </div>

        {/* ── LATENCY + INTERESTS ROW ────────────────────────────────── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: '1rem' }}>

          {/* Latency line chart */}
          <div style={card()}>
            <h2 style={{ margin: '0 0 1.25rem', fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>⚡ Response Latency (ms)</h2>
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={liveData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
                <XAxis dataKey="time" stroke="#475569" tick={{ fontSize: 10, fill: '#64748b' }} />
                <YAxis stroke="#475569" tick={{ fontSize: 10, fill: '#64748b' }} />
                <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: '0.75rem', fontSize: '0.8rem' }} formatter={() => [`${latency.toFixed(1)} ms`, 'Latency']} />
                <Line type="monotone" dataKey="recs" name="Latency" stroke="#f59e0b" strokeWidth={2.5} dot={false} />
              </LineChart>
            </ResponsiveContainer>
            <div style={{ display: 'flex', gap: '1rem', marginTop: '0.75rem' }}>
              {[
                { label: 'Avg', value: `${latency.toFixed(1)}ms`, color: '#10b981' },
                { label: 'P95', value: `${(metrics.recommendations.p95_latency_ms||0).toFixed(0)}ms`, color: '#f59e0b' },
                { label: 'Version', value: metrics.model.version || 'v1', color: '#6366f1' },
              ].map(({ label, value, color }) => (
                <div key={label} style={{ flex: 1, background: `${color}18`, border: `1px solid ${color}33`, borderRadius: '0.75rem', padding: '0.6rem', textAlign: 'center' }}>
                  <div style={{ fontSize: '0.95rem', fontWeight: 700, color }}>{value}</div>
                  <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{label}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Top Interests bar chart */}
          <div style={card()}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.25rem', flexWrap: 'wrap' }}>
              <h2 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)', flex: 1 }}>🧠 User Interest Vector</h2>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <input
                  placeholder="user ID…"
                  value={profileInput}
                  onChange={e => setProfileInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && setProfileUserId(profileInput.trim())}
                  style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: '0.6rem', padding: '0.4rem 0.75rem', color: 'white', outline: 'none', width: '150px', fontSize: '0.8rem' }}
                />
                <button
                  onClick={() => setProfileUserId(profileInput.trim())}
                  disabled={!profileInput.trim()}
                  style={{ padding: '0.4rem 0.9rem', borderRadius: '0.6rem', background: 'linear-gradient(135deg,#6366f1,#ec4899)', border: 'none', color: 'white', cursor: 'pointer', fontSize: '0.8rem', fontWeight: 600 }}
                >Track</button>
              </div>
            </div>
            {profileUserId && topInterests && topInterests.length > 0 ? (
              <>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', margin: '0 0 0.75rem' }}>
                  <span style={{ color: '#a78bfa', fontWeight: 600 }}>{profileUserId}</span> · live · updates on every interaction
                </p>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={topInterests} layout="vertical" margin={{ left: 10, right: 40, top: 0, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" horizontal={false} />
                    <XAxis type="number" domain={[0,1]} stroke="#475569" tick={{ fontSize: 10, fill: '#64748b' }} tickFormatter={v => `${Math.round(v*100)}%`} />
                    <YAxis type="category" dataKey="label" stroke="#475569" tick={{ fontSize: 11, fill: '#94a3b8' }} width={85} />
                    <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid rgba(148,163,184,0.2)', borderRadius: '0.75rem', fontSize: '0.8rem' }} formatter={(v: number) => [`${Math.round(v*100)}%`, 'Interest']} />
                    <Bar dataKey="weight" radius={[0,6,6,0]} minPointSize={4} label={{ position: 'right', fontSize: 11, fill: '#94a3b8', formatter: (v: number) => `${Math.round(v*100)}%` }}>
                      {topInterests.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '220px', gap: '0.75rem', color: 'var(--text-muted)' }}>
                <div style={{ fontSize: '3rem' }}>🎭</div>
                <p style={{ textAlign: 'center', fontSize: '0.85rem', maxWidth: '260px', lineHeight: 1.5 }}>
                  {profileUserId ? `No profile found for "${profileUserId}". Create one with ➕ New User.` : 'Enter a user ID to see their interest vector update in real-time as they interact with movies.'}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* ── FOOTER ─────────────────────────────────────────────────── */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', paddingTop: '0.5rem' }}>
          <div style={{ width: '8px', height: '8px', borderRadius: '50%', background: '#10b981', boxShadow: isLive ? '0 0 8px #10b981' : 'none', transition: 'box-shadow 0.5s' }} />
          <span style={{ color: 'var(--text-muted)', fontSize: '0.75rem' }}>Refreshing every 3s · {new Date().toLocaleTimeString()}</span>
        </div>

      </div>
    </div>
  );
}
