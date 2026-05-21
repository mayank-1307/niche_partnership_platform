import { motion } from "framer-motion";
import { Activity, Sparkles } from "lucide-react";

type Log = { ts: string; agent: string; message: string };

export function AgentActivity({ logs, loading }: { logs: Log[]; loading: boolean }) {
  return (
    <div className="glass rounded-2xl p-5">
      <div className="mb-3 flex items-center gap-2 text-sm text-cyan">
        <Activity className="h-4 w-4" />
        Agent Activity
      </div>
      <div className="space-y-2 text-sm">
        {logs.map((log, idx) => (
          <motion.div
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.04 }}
            key={`${log.ts}-${idx}`}
            className="rounded-xl border border-white/10 bg-black/20 p-3"
          >
            <div className="text-xs text-slate-400">{new Date(log.ts).toLocaleTimeString()} • {log.agent}</div>
            <div>{log.message}</div>
          </motion.div>
        ))}
        {loading && (
          <div className="flex items-center gap-2 text-mint">
            <Sparkles className="h-4 w-4 animate-pulse" /> Thinking...
          </div>
        )}
      </div>
    </div>
  );
}
