import React from 'react';
import { Play, RotateCcw, AlertTriangle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface TaskBarProps {
  taskPrompt: string;
  setTaskPrompt: (p: string) => void;
  targetUrl: string;
  setTargetUrl: (u: string) => void;
  onInspect: () => void;
  onSimulateCanaryLeak: () => void;
  onReset: () => void;
  isSimulatingLeak: boolean;
  isLoading: boolean;
}

export const TaskBar: React.FC<TaskBarProps> = ({
  taskPrompt,
  setTaskPrompt,
  targetUrl,
  setTargetUrl,
  onInspect,
  onSimulateCanaryLeak,
  onReset,
  isSimulatingLeak,
  isLoading,
}) => {
  return (
    <div className="bg-card border border-border rounded-xl p-4 shadow-sm space-y-3">
      {/* Row 1: Task prompt + URL */}
      <div className="flex flex-col md:flex-row gap-3">
        <div className="flex-1">
          <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">
            Target Browser Automation Task
          </label>
          <input
            type="text"
            value={taskPrompt}
            onChange={(e) => setTaskPrompt(e.target.value)}
            placeholder="e.g. Enter passenger details and proceed to payment for flight 6E-204"
            className="w-full bg-secondary/50 border border-border focus:border-primary/80 rounded-lg px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground/60 transition-all font-mono"
          />
        </div>

        <div className="md:w-72">
          <label className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">
            Target URL <span className="text-muted-foreground/50">(blank = demo page)</span>
          </label>
          <input
            type="url"
            value={targetUrl}
            onChange={(e) => setTargetUrl(e.target.value)}
            placeholder="https://example.com  (leave blank for demo)"
            className="w-full bg-secondary/50 border border-border focus:border-primary/80 rounded-lg px-4 py-2.5 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-primary placeholder:text-muted-foreground/60 transition-all font-mono"
          />
        </div>
      </div>

      {/* Row 2: Action buttons */}
      <div className="flex items-center gap-2 flex-wrap">
        <Button onClick={onInspect} disabled={isLoading} className="gap-2 shrink-0">
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Play className="h-4 w-4 fill-current" />
          )}
          {isLoading ? 'Inspecting…' : 'Inspect & Sanitize Page'}
        </Button>

        <Button
          variant={isSimulatingLeak ? 'destructive' : 'outline'}
          onClick={onSimulateCanaryLeak}
          disabled={isLoading}
          className="gap-2 shrink-0"
          title="Inject an unredacted secret canary into outbound payload to test Fail-Closed Firewall enforcement"
        >
          <AlertTriangle className="h-4 w-4 text-amber-400" />
          {isSimulatingLeak ? 'Canary Leaked (Firewall Tripped)' : 'Simulate Canary Attack'}
        </Button>

        <Button variant="ghost" size="icon" onClick={onReset} title="Reset to baseline" disabled={isLoading}>
          <RotateCcw className="h-4 w-4 text-muted-foreground" />
        </Button>

        <span className="ml-auto text-xs text-muted-foreground/60 font-mono hidden sm:inline">
          Origin:{' '}
          <span className="text-cyan-400">
            {targetUrl ? new URL(targetUrl.startsWith('http') ? targetUrl : `https://${targetUrl}`).hostname : 'air-express.internal'}
          </span>
        </span>
      </div>
    </div>
  );
};
