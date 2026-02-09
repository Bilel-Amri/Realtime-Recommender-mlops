import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import axios from 'axios';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000/api/v1';

export default function ABTestingPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['abTestResults'],
    queryFn: async () => {
      const response = await axios.get(`${API_BASE_URL}/mlops/ab-results-demo`);
      return response.data;
    },
  });

  if (isLoading || !data) return <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-900 to-purple-900 flex items-center justify-center">
    <div className="animate-spin rounded-full h-12 w-12 border-4 border-green-500 border-t-transparent"></div>
  </div>;

  const variantA = data.variants[0];
  const variantB = data.variants[1];
  const comparison = data.comparison;

  const metricsData = [
    { metric: 'Click', A: (variantA.metrics.click_rate * 100), B: (variantB.metrics.click_rate * 100) },
    { metric: 'Like', A: (variantA.metrics.like_rate * 100), B: (variantB.metrics.like_rate * 100) },
    { metric: 'Engage', A: (variantA.metrics.engagement_rate * 100), B: (variantB.metrics.engagement_rate * 100) },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-900 to-purple-900 text-white p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Giant Winner Banner */}
        <div className="relative bg-gradient-to-r from-green-500 via-emerald-500 to-green-600 rounded-3xl p-12 shadow-2xl overflow-hidden">
          <div className="absolute top-0 right-0 text-[200px] opacity-10">🏆</div>
          <div className="relative z-10">
            <div className="text-green-100 text-xl font-bold mb-3 tracking-widest">🎉 WINNER</div>
            <h1 className="text-7xl font-black mb-4">{comparison.winner}</h1>
            <div className="flex items-center gap-4">
              <div className="text-5xl font-bold">+{comparison.engagement_improvement.toFixed(1)}%</div>
              <div className="text-2xl text-green-100">Better Engagement</div>
            </div>
          </div>
        </div>

        {/* Side-by-Side Comparison */}
        <div className="grid grid-cols-2 gap-8">
          
          {/* Model A */}
          <div className="bg-gray-800/50 backdrop-blur rounded-3xl p-8 border-2 border-gray-700">
            <div className="flex items-center justify-between mb-6">
              <div>
                <div className="text-4xl mb-2">📊</div>
                <h2 className="text-3xl font-bold">Model A</h2>
                <p className="text-gray-400">Baseline</p>
              </div>
              <span className="px-4 py-2 bg-gray-700 rounded-full text-sm">OLD</span>
            </div>
            
            {/* Stats Grid */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-gray-700/50 rounded-2xl p-5">
                <div className="text-4xl font-bold mb-1">{(variantA.metrics.click_rate * 100).toFixed(1)}%</div>
                <div className="text-gray-400 text-sm">Click</div>
              </div>
              <div className="bg-gray-700/50 rounded-2xl p-5">
                <div className="text-4xl font-bold mb-1">{(variantA.metrics.like_rate * 100).toFixed(1)}%</div>
                <div className="text-gray-400 text-sm">Like</div>
              </div>
              <div className="bg-gray-700/50 rounded-2xl p-5">
                <div className="text-4xl font-bold mb-1">{(variantA.metrics.engagement_rate * 100).toFixed(1)}%</div>
                <div className="text-gray-400 text-sm">Engage</div>
              </div>
              <div className="bg-gray-700/50 rounded-2xl p-5">
                <div className="text-4xl font-bold mb-1">{variantA.metrics.avg_rating.toFixed(1)}</div>
                <div className="text-gray-400 text-sm">Rating</div>
              </div>
            </div>

            {/* Mini Stats */}
            <div className="space-y-2 text-sm">
              <div className="flex justify-between text-gray-400">
                <span>Users</span>
                <span className="text-white font-bold">{variantA.users.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-gray-400">
                <span>Clicks</span>
                <span className="text-white font-bold">{variantA.clicks.toLocaleString()}</span>
              </div>
            </div>
          </div>

          {/* Model B - Winner */}
          <div className="bg-gradient-to-br from-green-900/40 to-emerald-900/40 backdrop-blur rounded-3xl p-8 border-2 border-green-500 shadow-lg shadow-green-500/20">
            <div className="flex items-center justify-between mb-6">
              <div>
                <div className="text-4xl mb-2">🚀</div>
                <h2 className="text-3xl font-bold">Model B</h2>
                <p className="text-green-300">Retrained</p>
              </div>
              <span className="px-4 py-2 bg-green-500 text-white rounded-full text-sm font-bold animate-pulse">WINNER</span>
            </div>
            
            {/* Stats Grid with Deltas */}
            <div className="grid grid-cols-2 gap-4 mb-6">
              <div className="bg-green-500/10 rounded-2xl p-5 border border-green-500/30">
                <div className="flex items-baseline gap-2 mb-1">
                  <div className="text-4xl font-bold">{(variantB.metrics.click_rate * 100).toFixed(1)}%</div>
                  <div className="text-green-400 text-xl font-bold">↑{comparison.click_rate_improvement.toFixed(0)}%</div>
                </div>
                <div className="text-gray-400 text-sm">Click</div>
              </div>
              <div className="bg-green-500/10 rounded-2xl p-5 border border-green-500/30">
                <div className="flex items-baseline gap-2 mb-1">
                  <div className="text-4xl font-bold">{(variantB.metrics.like_rate * 100).toFixed(1)}%</div>
                  <div className="text-green-400 text-xl font-bold">↑{comparison.like_rate_improvement.toFixed(0)}%</div>
                </div>
                <div className="text-gray-400 text-sm">Like</div>
              </div>
              <div className="bg-green-500/10 rounded-2xl p-5 border border-green-500/30">
                <div className="flex items-baseline gap-2 mb-1">
                  <div className="text-4xl font-bold">{(variantB.metrics.engagement_rate * 100).toFixed(1)}%</div>
                  <div className="text-green-400 text-xl font-bold">↑{comparison.engagement_improvement.toFixed(0)}%</div>
                </div>
                <div className="text-gray-400 text-sm">Engage</div>
              </div>
              <div className="bg-green-500/10 rounded-2xl p-5 border border-green-500/30">
                <div className="flex items-baseline gap-2 mb-1">
                  <div className="text-4xl font-bold">{variantB.metrics.avg_rating.toFixed(1)}</div>
                  <div className="text-green-400 text-xl font-bold">↑{comparison.rating_improvement.toFixed(0)}%</div>
                </div>
                <div className="text-gray-400 text-sm">Rating</div>
              </div>
            </div>

            {/* Mini Stats */}
            <div className="space-y-2 text-sm">
              <div className="flex justify-between text-gray-400">
                <span>Users</span>
                <span className="text-white font-bold">{variantB.users.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-gray-400">
                <span>Clicks</span>
                <span className="text-white font-bold">{variantB.clicks.toLocaleString()}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Chart */}
        <div className="bg-gray-800/50 backdrop-blur rounded-3xl p-8 border border-gray-700/50">
          <div className="flex items-center gap-3 mb-6">
            <div className="text-3xl">📊</div>
            <h2 className="text-2xl font-bold">Performance Comparison</h2>
          </div>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={metricsData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="metric" stroke="#9ca3af" />
              <YAxis stroke="#9ca3af" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '12px' }}
                labelStyle={{ color: '#fff', fontWeight: 'bold' }}
              />
              <Bar dataKey="A" fill="#6b7280" radius={[8, 8, 0, 0]} />
              <Bar dataKey="B" fill="#10b981" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Stats Pills */}
        <div className="grid grid-cols-3 gap-6">
          <div className="bg-gray-800/50 backdrop-blur rounded-2xl p-6 border border-gray-700/50">
            <div className="text-3xl mb-3">✓</div>
            <div className="text-4xl font-bold mb-2 text-green-400">Significant</div>
            <div className="text-gray-400 text-sm">p = {comparison.p_value.toFixed(4)}</div>
          </div>

          <div className="bg-gray-800/50 backdrop-blur rounded-2xl p-6 border border-gray-700/50">
            <div className="text-3xl mb-3">🎯</div>
            <div className="text-4xl font-bold mb-2 text-blue-400">{(comparison.confidence_level * 100).toFixed(0)}%</div>
            <div className="text-gray-400 text-sm">Confidence</div>
          </div>

          <div className="bg-gray-800/50 backdrop-blur rounded-2xl p-6 border border-gray-700/50">
            <div className="text-3xl mb-3">⏱️</div>
            <div className="text-4xl font-bold mb-2 text-purple-400">{data.experiment.duration_hours}h</div>
            <div className="text-gray-400 text-sm">Duration</div>
          </div>
        </div>

        {/* Deploy Decision */}
        <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-3xl p-10 shadow-2xl">
          <div className="flex items-center gap-6">
            <div className="text-7xl">🚀</div>
            <div className="flex-1">
              <h2 className="text-3xl font-bold mb-2">{data.recommendation.action}</h2>
              <p className="text-blue-100 text-xl mb-3">{data.recommendation.reason}</p>
              <div className="flex gap-3">
                <span className="px-4 py-2 bg-white/20 rounded-full text-sm">Impact: {data.recommendation.estimated_impact}</span>
                <span className="px-4 py-2 bg-white/20 rounded-full text-sm">{data.experiment.total_users.toLocaleString()} users tested</span>
              </div>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
