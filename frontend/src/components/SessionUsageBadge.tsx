import React, { useState, useEffect, useCallback } from 'react';
import { Zap, MessageSquare } from 'lucide-react';
import { llmUsageApi } from '../services/llmUsageApi';
import { formatNumber, formatCurrency } from '../utils/formatUtils';

interface SessionUsageBadgeProps {
  sessionId: string;
}

export const SessionUsageBadge: React.FC<SessionUsageBadgeProps> = ({
  sessionId,
}) => {
  const [usage, setUsage] = useState<any>(null);

  const fetchUsage = useCallback(async () => {
    if (!sessionId) return;
    try {
      const data = await llmUsageApi.getSessionUsage(sessionId);
      setUsage(data);
    } catch (error) {
      console.error('Error fetching session usage:', error);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchUsage();

    const interval = setInterval(() => {
      if (document.visibilityState === 'visible') {
        fetchUsage();
      }
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchUsage]);

  if (!usage || usage.total_calls === 0) return null;

  return (
    <div className="flex items-center gap-4 px-4 py-1.5 glass-panel rounded-xl text-[10px] font-black uppercase tracking-widest text-slate-500 animate-fadeIn">
      <div className="flex items-center gap-1.5 group cursor-help" title="Total tokens used in this session">
        <Zap className="w-3 h-3 text-yellow-500/80 group-hover:scale-110 transition-transform" />
        <span className="text-slate-700 dark:text-slate-300">{formatNumber(usage.total_tokens)}</span>
      </div>
      <div className="w-px h-3 bg-slate-700/30" />
      <div className="flex items-center gap-1.5 group cursor-help" title="Total LLM calls in this session">
        <MessageSquare className="w-3 h-3 text-blue-500/80 group-hover:scale-110 transition-transform" />
        <span className="text-slate-700 dark:text-slate-300">{usage.total_calls}</span>
      </div>
      {usage.total_cost_usd > 0 && (
        <>
          <div className="w-px h-3 bg-slate-700/30" />
          <div className="flex items-center gap-1 group cursor-help text-amber-600 dark:text-amber-400" title="Estimated cost of this session">
            <span>{formatCurrency(usage.total_cost_usd)}</span>
          </div>
        </>
      )}
    </div>
  );
};
