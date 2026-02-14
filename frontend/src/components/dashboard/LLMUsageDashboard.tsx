import React, { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  AreaChart, Area, Cell, PieChart, Pie
} from 'recharts';
import {
  Activity, Zap, MessageSquare, Clock, Shield, Database,
  BarChart2, PieChart as PieChartIcon, TrendingUp, Calendar
} from 'lucide-react';
import { llmUsageApi, LLMUsageStats, LLMUsageByAgent, LLMUsageTimeSeries, LLMUsageRecord } from '../../services/llmUsageApi';
import { formatNumber, formatCurrency } from '../../utils/formatUtils';

export const LLMUsageDashboard: React.FC = () => {
  const [timeRange, setTimeRange] = useState<number>(7);
  const [stats, setStats] = useState<LLMUsageStats | null>(null);
  const [byAgent, setByAgent] = useState<LLMUsageByAgent[]>([]);
  const [byModel, setByModel] = useState<any[]>([]);
  const [byProvider, setByProvider] = useState<any[]>([]);
  const [timeseries, setTimeseries] = useState<LLMUsageTimeSeries[]>([]);
  const [recentCalls, setRecentCalls] = useState<LLMUsageRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [statsData, agentData, modelData, providerData, tsData, recentData] = await Promise.all([
        llmUsageApi.getStats(timeRange),
        llmUsageApi.getByAgent(timeRange),
        llmUsageApi.getByModel(timeRange),
        llmUsageApi.getByProvider(timeRange),
        llmUsageApi.getTimeSeries(timeRange, timeRange > 2 ? 'day' : 'hour'),
        llmUsageApi.getRecent(50)
      ]);

      setStats(statsData);
      setByAgent(agentData);
      setByModel(modelData);
      setByProvider(providerData);
      setTimeseries(tsData);
      setRecentCalls(recentData);
    } catch (error) {
      console.error('Error fetching usage data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [timeRange]);

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

  if (isLoading && !stats) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6 overflow-y-auto h-full text-slate-200 bg-slate-900/50">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2">
            <Activity className="text-blue-400" />
            LLM Usage Monitoring
          </h1>
          <p className="text-slate-400">Track token consumption and agent performance</p>
        </div>

        <div className="flex bg-slate-800 rounded-lg p-1">
          {[
            { label: '24h', value: 1 },
            { label: '7d', value: 7 },
            { label: '30d', value: 30 },
            { label: '90d', value: 90 }
          ].map((range) => (
            <button
              key={range.value}
              onClick={() => setTimeRange(range.value)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                timeRange === range.value
                  ? 'bg-blue-600 text-white shadow-lg'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {range.label}
            </button>
          ))}
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard
          title="Total Tokens"
          value={formatNumber(stats?.total_tokens)}
          subValue={`${formatNumber(stats?.total_input_tokens)} in / ${formatNumber(stats?.total_output_tokens)} out`}
          icon={<Zap className="w-5 h-5 text-yellow-400" />}
        />
        <StatCard
          title="Total LLM Calls"
          value={formatNumber(stats?.total_calls)}
          subValue={`${stats?.unique_sessions || 0} active sessions`}
          icon={<MessageSquare className="w-5 h-5 text-blue-400" />}
        />
        <StatCard
          title="Avg Latency"
          value={`${stats?.avg_response_time_ms?.toFixed(0) || 0}ms`}
          subValue="Response time"
          icon={<Clock className="w-5 h-5 text-emerald-400" />}
        />
        <StatCard
          title="Total Cost"
          value={formatCurrency(stats?.total_cost_usd)}
          subValue="Estimated USD"
          icon={<Database className="w-5 h-5 text-blue-400" />}
        />
        <StatCard
          title="Models Used"
          value={stats?.models_used.toString() || '0'}
          subValue="Active LLM models"
          icon={<Shield className="w-5 h-5 text-purple-400" />}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Token Usage Chart */}
        <div className="lg:col-span-2 bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6 shadow-xl">
          <div className="flex justify-between items-center mb-6">
            <h3 className="font-semibold text-white flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-400" />
              Token Usage Over Time
            </h3>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={timeseries}>
                <defs>
                  <linearGradient id="colorTokens" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis
                  dataKey="period"
                  stroke="#94a3b8"
                  fontSize={12}
                  tickFormatter={(val) => {
                    if (timeRange <= 2) return val.split(' ')[1];
                    return val.split('-').slice(1).join('/');
                  }}
                />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#f1f5f9' }}
                  itemStyle={{ color: '#60a5fa' }}
                />
                <Area
                  type="monotone"
                  dataKey="total_tokens"
                  stroke="#3b82f6"
                  fillOpacity={1}
                  fill="url(#colorTokens)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Agent Breakdown */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6 shadow-xl">
          <h3 className="font-semibold text-white mb-6 flex items-center gap-2">
            <PieChartIcon className="w-4 h-4 text-purple-400" />
            Usage by Agent
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={byAgent as any[]}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={80}
                  paddingAngle={5}
                  dataKey="total_tokens"
                  nameKey="agent_type"
                >
                  {byAgent.map((_entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Model Breakdown */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6 shadow-xl">
          <h3 className="font-semibold text-white mb-6 flex items-center gap-2">
            <BarChart2 className="w-4 h-4 text-emerald-400" />
            Tokens by Model
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byModel} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                <XAxis type="number" stroke="#94a3b8" fontSize={12} />
                <YAxis dataKey="model_name" type="category" stroke="#94a3b8" fontSize={10} width={80} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                />
                <Bar dataKey="total_tokens" fill="#10b981" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Provider Breakdown */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6 shadow-xl">
          <h3 className="font-semibold text-white mb-6 flex items-center gap-2">
            <Database className="w-4 h-4 text-blue-400" />
            Tokens by Provider
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byProvider} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" horizontal={false} />
                <XAxis type="number" stroke="#94a3b8" fontSize={12} />
                <YAxis dataKey="provider" type="category" stroke="#94a3b8" fontSize={10} width={80} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                />
                <Bar dataKey="total_tokens" fill="#3b82f6" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Latency by Agent */}
        <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-6 shadow-xl">
          <h3 className="font-semibold text-white mb-6 flex items-center gap-2">
            <Clock className="w-4 h-4 text-yellow-400" />
            Avg Latency by Agent (ms)
          </h3>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={byAgent}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                <XAxis dataKey="agent_type" stroke="#94a3b8" fontSize={10} />
                <YAxis stroke="#94a3b8" fontSize={12} />
                <Tooltip
                  contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                />
                <Bar dataKey="avg_response_time_ms" fill="#f59e0b" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Recent LLM Calls Table */}
      <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 overflow-hidden shadow-xl">
        <div className="p-6 border-b border-slate-700/50 flex justify-between items-center">
          <h3 className="font-semibold text-white flex items-center gap-2">
            <Calendar className="w-4 h-4 text-blue-400" />
            Recent LLM Transactions
          </h3>
          <button
            onClick={fetchData}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            Refresh data
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="bg-slate-800/80 text-slate-400 text-xs uppercase tracking-wider">
                <th className="px-6 py-3 font-medium">Time</th>
                <th className="px-6 py-3 font-medium">Agent</th>
                <th className="px-6 py-3 font-medium">Provider</th>
                <th className="px-6 py-3 font-medium">Model</th>
                <th className="px-6 py-3 font-medium text-right">Tokens</th>
                <th className="px-6 py-3 font-medium text-right">Cost</th>
                <th className="px-6 py-3 font-medium text-right">Latency</th>
                <th className="px-6 py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {recentCalls.map((call) => (
                <tr key={call.id} className="hover:bg-slate-700/30 transition-colors text-sm">
                  <td className="px-6 py-4 text-slate-400 whitespace-nowrap">
                    {new Date(call.created_at).toLocaleTimeString()}
                  </td>
                  <td className="px-6 py-4 font-medium text-slate-200">
                    <span className="px-2 py-0.5 rounded bg-slate-700 text-slate-300 text-[10px]">
                      {call.agent_type}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-slate-300 capitalize">
                    {call.provider}
                  </td>
                  <td className="px-6 py-4 text-slate-300 whitespace-nowrap">
                    {call.model_name}
                  </td>
                  <td className="px-6 py-4 text-right text-slate-300 font-mono">
                    {formatNumber(call.input_tokens + call.output_tokens)}
                  </td>
                  <td className="px-6 py-4 text-right text-amber-400/80 font-mono">
                    {call.estimated_cost_usd != null && call.estimated_cost_usd > 0 ? `$${call.estimated_cost_usd.toFixed(4)}` : '-'}
                  </td>
                  <td className="px-6 py-4 text-right text-slate-300">
                    {call.response_time_ms?.toFixed(0)}ms
                  </td>
                  <td className="px-6 py-4">
                    {call.success ? (
                      <span className="flex items-center gap-1 text-emerald-400 text-xs">
                        <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                        Success
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 text-red-400 text-xs">
                        <div className="w-1.5 h-1.5 rounded-full bg-red-400" />
                        Failed
                      </span>
                    )}
                  </td>
                </tr>
              ))}
              {recentCalls.length === 0 && (
                <tr>
                  <td colSpan={8} className="px-6 py-8 text-center text-slate-500 italic">
                    No recent LLM transactions found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

interface StatCardProps {
  title: string;
  value: string;
  subValue: string;
  icon: React.ReactNode;
}

const StatCard: React.FC<StatCardProps> = ({ title, value, subValue, icon }) => (
  <div className="bg-slate-800/50 backdrop-blur-sm rounded-xl border border-slate-700/50 p-5 shadow-lg">
    <div className="flex justify-between items-start mb-2">
      <h4 className="text-slate-400 text-sm font-medium">{title}</h4>
      <div className="bg-slate-700/50 p-2 rounded-lg">{icon}</div>
    </div>
    <div className="text-2xl font-bold text-white mb-1">{value}</div>
    <div className="text-xs text-slate-500 font-medium">{subValue}</div>
  </div>
);
