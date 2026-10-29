import React from 'react';
import { Play, RotateCcw, AlertTriangle, ShieldCheck, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface TaskBarProps {
  taskPrompt: string;
  setTaskPrompt: (p: string) => void;
  onInspect: () => void;
  onSimulateCanaryLeak: () => void;
  onReset: () => void;
  isSimulatingLeak: boolean;
}

export const TaskBar: React.FC<TaskBarProps> = ({
  taskPrompt,
  setTaskPrompt,
  onInspect,
  onSimulateCanaryLeak,
  onReset,
  isSimulatingLeak,
}) => {
  return (
    <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
      <div className="flex flex-col md:flex-row items-stretch md:items-center gap-3">
        <div className="flex-1 relative">
          <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">
            Target Browser Automation Task
          </label>
          <div className="relative flex items-center">
            <input
              type="text"
              value={taskPrompt}
              onChange={(e) => setTaskPrompt(e.target.value)}
              placeholder="e.g. Enter passenger details and proceed to payment for flight 6E-204"
              className="w-full bg-secondary/50 border border-border focus:border-primary/80 rounded-lg px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground/60 transition-all font-mono"
            />
            <span className="absolute right-3 text-xs text-muted-foreground/70 hidden sm:inline">
              Target Origin: <span className="text-cyan-400 font-mono">air-express.internal</span>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 pt-2 md:pt-5">
          <Button onClick={onInspect} className="gap-2 shrink-0">
            <Play className="h-4 w-4 fill-current" />
            Inspect & Sanitize Page
          </Button>

          <Button
            variant={isSimulatingLeak ? "destructive" : "outline"}
            onClick={onSimulateCanaryLeak}
            className="gap-2 shrink-0"
            title="Inject an unredacted secret canary into outbound payload to test Fail-Closed Firewall enforcement"
          >
            <AlertTriangle className="h-4 w-4 text-amber-400" />
            {isSimulatingLeak ? "Canary Leaked (Firewall Tripped)" : "Simulate Canary Attack"}
          </Button>

          <Button variant="ghost" size="icon" onClick={onReset} title="Reset to baseline">
            <RotateCcw className="h-4 w-4 text-muted-foreground" />
          </Button>
        </div>
      </div>
    </div>
  );
};
