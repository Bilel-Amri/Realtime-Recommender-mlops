import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AreaChart, Area, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { metricsApi } from '../services/api';

const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

export default function DashboardPage() {
  const [historicalData, setHistoricalData] = useState<Array<{
    time: string;
    events: number;
  }>>([]);

  const { data: metrics } = useQuery({
    queryKey: ['dashboardMetrics'],
    queryFn: metricsApi.getDashboardMetrics,
    refetchInterval: 5000,
  });

  useEffect(() => {
    if (metrics) {
      const now = new Date();
      const timeStr = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
      
      setHistoricalData((prev) => {
        const newData = [...prev, {
          time: timeStr,
          events: metrics.events.total,
        }];
        return newData.slice(-20);
      });
    }
  }, [metrics]);

  if (!metrics) return <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-900 to-blue-900 flex items-center justify-center">
    <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
  </div>;

  const eventTypesData = metrics.events.by_type ? Object.entries(metrics.events.by_type).map(([name, value]) => ({
    name, value
  })) : [];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-900 to-blue-900 text-white p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="text-5xl animate-pulse">🤖</div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
              AI Monitor
            </h1>
          </div>
          <div className="flex items-center gap-2 bg-green-500/20 px-6 py-3 rounded-full border-2 border-green-500 animate-pulse">
            <div className="w-3 h-3 bg-green-400 rounded-full"></div>
            <span className="text-lg text-green-300 font-bold">LIVE</span>
          </div>
        </div>

        {/* Giant KPI Cards */}
        <div className="grid grid-cols-4 gap-6">
          <div className="group bg-gradient-to-br from-blue-500 to-blue-600 rounded-3xl p-8 shadow-2xl hover:scale-110 hover:rotate-1 transition-all duration-300 cursor-pointer">
            <div className="text-7xl mb-4 group-hover:scale-125 transition-transform">⚡</div>
            <div className="text-6xl font-black mb-2">{metrics.events.total}</div>
            <div className="text-blue-100 text-sm opacity-70">{metrics.events.per_minute?.toFixed(1)}/min</div>
          </div>

          <div className="group bg-gradient-to-br from-green-500 to-emerald-600 rounded-3xl p-8 shadow-2xl hover:scale-110 hover:rotate-1 transition-all duration-300 cursor-pointer">
            <div className="text-7xl mb-4 group-hover:scale-125 transition-transform">🎯</div>
            <div className="text-6xl font-black mb-2">{metrics.recommendations.total}</div>
            <div className="text-green-100 text-sm opacity-70">{metrics.recommendations.average_latency_ms?.toFixed(0)}ms</div>
          </div>

          <div className="group bg-gradient-to-br from-purple-500 to-purple-600 rounded-3xl p-8 shadow-2xl hover:scale-110 hover:rotate-1 transition-all duration-300 cursor-pointer">
            <div className="text-7xl mb-4 group-hover:scale-125 transition-transform">🧠</div>
            <div className="text-6xl font-black mb-2">{metrics.learning.user_embeddings_updated}</div>
            <div className="text-purple-100 text-sm opacity-70">Learning</div>
          </div>

          <div className="group bg-gradient-to-br from-orange-500 to-red-500 rounded-3xl p-8 shadow-2xl hover:scale-110 hover:rotate-1 transition-all duration-300 cursor-pointer">
            <div className="text-7xl mb-4 group-hover:scale-125 transition-transform">⏱️</div>
            <div className="text-6xl font-black mb-2">
              {Math.floor((metrics.system.uptime_seconds || 0) / 3600)}
              <span className="text-3xl opacity-70">h</span>
            </div>
            <div className="text-orange-100 text-sm opacity-70">{Math.floor(((metrics.system.uptime_seconds || 0) % 3600) / 60)}min</div>
          </div>
        </div>

        {/* Chart Section */}
        <div className="grid grid-cols-3 gap-6">
          
          {/* Activity Chart */}
          <div className="col-span-2 bg-gray-800/50 backdrop-blur-xl rounded-3xl p-8 border border-gray-700/50 shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="text-3xl">📈</div>
              <h2 className="text-2xl font-bold">Activity Stream</h2>
            </div>
            <ResponsiveContainer width="100%" height={280}>
              <AreaChart data={historicalData}>
                <defs>
                  <linearGradient id="colorEvents" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.9}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                <XAxis dataKey="time" stroke="#9ca3af" tick={{ fontSize: 12 }} />
                <YAxis stroke="#9ca3af" tick={{ fontSize: 12 }} />
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '12px' }}
                  labelStyle={{ color: '#fff', fontWeight: 'bold' }}
                />
                <Area type="monotone" dataKey="events" stroke="#3b82f6" strokeWidth={3} fill="url(#colorEvents)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Donut Chart */}
          <div className="bg-gray-800/50 backdrop-blur-xl rounded-3xl p-8 border border-gray-700/50 shadow-2xl">
            <div className="flex items-center gap-3 mb-6">
              <div className="text-3xl">📊</div>
              <h2 className="text-2xl font-bold">Types</h2>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={eventTypesData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="value"
                >
                  {eventTypesData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '12px' }}
                />
              </PieChart>
            </ResponsiveContainer>
            <div className="mt-6 space-y-3">
              {eventTypesData.map((item, index) => (
                <div key={item.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-4 h-4 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }}></div>
                    <span className="font-semibold capitalize">{item.name}</span>
                  </div>
                  <span className="text-2xl font-bold">{item.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Compact Stats Grid */}
        <div className="grid grid-cols-6 gap-4">
          <div className="bg-gray-800/50 backdrop-blur rounded-2xl p-5 border border-gray-700/50">
            <div className="text-3xl mb-2">🎯</div>
            <div className="text-3xl font-bold text-green-400">{metrics.model.rmse?.toFixed(3)}</div>
            <div className="text-xs text-gray-400 mt-1">RMSE</div>
          </div>

          <div className="bg-gray-800/50 backdrop-blur rounded-2xl p-5 border border-gray-700/50">
            <div className="text-3xl mb-2">📊</div>
            <div className="text-3xl font-bold text-blue-400">{metrics.model.r2_score?.toFixed(3)}</div>
            <div className="text-xs text-gray-400 mt-1">R² Score</div>
          </div>

          <div className="bg-gray-800/50 backdrop-blur rounded-2xl p-5 border border-gray-700/50">
            <div className="text-3xl mb-2">🔟</div>
            <div className="text-3xl font-bold text-purple-400">{metrics.model.map_at_10?.toFixed(3)}</div>
            <div className="text-xs text-gray-400 mt-1">MAP@10</div>
          </div>

          <div className="bg-gray-800/50 backdrop-blur rounded-2xl p-5 border border-gray-700/50">
            <div className="text-3xl mb-2">⚡</div>
            <div className="text-3xl font-bold text-yellow-400">{metrics.system.cache_hit_rate?.toFixed(0)}%</div>
            <div className="text-xs text-gray-400 mt-1">Cache</div>
          </div>

          <div className="bg-gray-800/50 backdrop-blur rounded-2xl p-5 border border-gray-700/50">
            <div className="text-3xl mb-2">👥</div>
            <div className="text-3xl font-bold text-cyan-400">{metrics.feature_store?.total_users || 0}</div>
            <div className="text-xs text-gray-400 mt-1">Users</div>
          </div>

          <div className="bg-gray-800/50 backdrop-blur rounded-2xl p-5 border border-gray-700/50">
            <div className="text-3xl mb-2">🎬</div>
            <div className="text-3xl font-bold text-pink-400">{metrics.feature_store?.total_items || 0}</div>
            <div className="text-xs text-gray-400 mt-1">Items</div>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center text-gray-500 text-sm flex items-center justify-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
          <span>Auto-refresh 5s</span>
        </div>
      </div>
    </div>
  );
}
