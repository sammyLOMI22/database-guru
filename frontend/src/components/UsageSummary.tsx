import React, { useState, useEffect } from 'react';
import { BarChart2, ChevronDown, ChevronUp, Zap, Clock, MessageSquare } from 'lucide-react';
import { llmUsageApi } from '../services/llmUsageApi';

interface UsageSummaryProps {
  sessionId: string;
  queryId?: number;
}

export const UsageSummary: React.FC<UsageSummaryProps> = ({
  sessionId,
  queryId,
}) => {
  const [expanded, setExpanded] = useState(false);
  const [usage, setUsage] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchUsage = async () => {
    if (!sessionId) return;
    setIsLoading(true);
    try {
      const data = await llmUsageApi.getSessionUsage(sessionId);
      setUsage(data);
    } catch (error) {
      console.error('Error fetching usage:', error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (expanded && !usage) {
      fetchUsage();
    }
  }, [expanded]);

  const formatNumber = (num: number) => {
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
  };

  const formatCurrency = (num: number) => {
    if (!num || num < 0.01) return '<$0.01';
    return `$${num.toFixed(2)}`;
  };

  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="flex items-center gap-2 text-[10px] uppercase tracking-wider font-bold text-slate-500 hover:text-blue-400 transition-colors mt-2 group"
      >
        <BarChart2 className="w-3 h-3 group-hover:scale-110 transition-transform" />
        <span>View LLM Usage Stats</span>
        <ChevronDown className="w-3 h-3" />
      </button>
    );
  }

  return (
    <div className="mt-3 p-4 bg-slate-800/40 rounded-xl border border-slate-700/50 backdrop-blur-md animate-fadeIn">
      <div className="flex justify-between items-start mb-4">
        <div className="flex items-center gap-4">
          <div className="flex flex-col">
            <span className="text-[10px] text-slate-500 uppercase font-bold">Total Tokens</span>
            <div className="flex items-center gap-1.5 text-blue-400 font-bold">
              <Zap className="w-3.5 h-3.5" />
              <span>{usage ? formatNumber(usage.total_tokens) : '...'}</span>
            </div>
          </div>
          <div className="flex flex-col border-l border-slate-700/50 pl-4">
            <span className="text-[10px] text-slate-500 uppercase font-bold">LLM Calls</span>
            <div className="flex items-center gap-1.5 text-emerald-400 font-bold">
              <MessageSquare className="w-3.5 h-3.5" />
              <span>{usage ? usage.total_calls : '...'}</span>
            </div>
          </div>
          <div className="flex flex-col border-l border-slate-700/50 pl-4">
            <span className="text-[10px] text-slate-500 uppercase font-bold">Latency</span>
            <div className="flex items-center gap-1.5 text-purple-400 font-bold">
              <Clock className="w-3.5 h-3.5" />
              <span>{usage?.avg_response_time_ms ? `${usage.avg_response_time_ms.toFixed(0)}ms` : '...'}</span>
            </div>
          </div>
          {usage?.total_cost_usd > 0 && (
            <div className="flex flex-col border-l border-slate-700/50 pl-4">
              <span className="text-[10px] text-slate-500 uppercase font-bold">Est. Cost</span>
              <div className="flex items-center gap-1.5 text-amber-400 font-bold">
                <span>{formatCurrency(usage.total_cost_usd)}</span>
              </div>
            </div>
          )}
        </div>
        <button
          onClick={() => setExpanded(false)}
          className="text-slate-500 hover:text-slate-300 p-1 rounded-lg hover:bg-slate-700/50 transition-all"
        >
          <ChevronUp className="w-4 h-4" />
        </button>
      </div>

      {usage && usage.by_agent && (
        <div className="space-y-3 mt-4">
          <div className="text-[10px] text-slate-400 uppercase font-black tracking-widest">Agent Breakdown</div>
          <div className="grid grid-cols-1 gap-2">
            {Object.entries(usage.by_agent).map(([agent, tokens]: [string, any]) => (
              <div key={agent} className="flex flex-col gap-1">
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-300 font-medium capitalize">{agent.replace(/_/g, ' ')}</span>
                  <span className="text-slate-400 font-mono">{formatNumber(tokens)} tokens</span>
                </div>
                <div className="h-1.5 w-full bg-slate-700/50 rounded-full overflow-hidden">
                  <div
                    className="h-full bg-blue-500 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.5)]"
                    style={{ width: `${Math.min(100, (tokens / usage.total_tokens) * 100)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {isLoading && (
        <div className="flex justify-center py-4">
          <div className="animate-pulse flex space-x-2">
            <div className="h-1.5 w-1.5 bg-blue-400 rounded-full"></div>
            <div className="h-1.5 w-1.5 bg-blue-400 rounded-full"></div>
            <div className="h-1.5 w-1.5 bg-blue-400 rounded-full"></div>
          </div>
        </div>
      )}
    </div>
  );
};
