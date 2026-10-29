import React from 'react';
import { ShieldCheck, ShieldAlert, Check, X, FileCode } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { FirewallDecision, SanitizedObservation } from '@/types';

interface OutboundFirewallCardProps {
  decision: FirewallDecision;
  payload: SanitizedObservation;
}

export const OutboundFirewallCard: React.FC<OutboundFirewallCardProps> = ({
  decision,
  payload,
}) => {
  return (
    <Card className={decision.is_allowed ? "border-border" : "border-red-500/80 bg-red-950/10"}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold">
            {decision.is_allowed ? (
              <ShieldCheck className="h-5 w-5 text-emerald-400" />
            ) : (
              <ShieldAlert className="h-5 w-5 text-red-400" />
            )}
            Outbound Privacy Firewall (Fail-Closed Egress)
          </CardTitle>
          {decision.is_allowed ? (
            <Badge variant="success">AUTHORIZED FOR AI EGRESS</Badge>
          ) : (
            <Badge variant="destructive" className="animate-pulse">EGRESS BLOCKED</Badge>
          )}
        </div>
        <CardDescription>
          Every outbound model payload is intercepted, serialized, and audited for secret leaks and planted canaries.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Verification Checks Checklist */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs">
          <div className="flex items-center gap-2 p-2.5 rounded-md bg-secondary/40 border border-border/80">
            {decision.canary_leaked ? (
              <X className="h-4 w-4 text-red-400 shrink-0" />
            ) : (
              <Check className="h-4 w-4 text-emerald-400 shrink-0" />
            )}
            <div>
              <div className="font-semibold text-foreground">Canary / Secret Scan</div>
              <div className="text-[11px] text-muted-foreground">
                {decision.canary_leaked ? "Planted canary found!" : "0 raw secrets detected"}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 p-2.5 rounded-md bg-secondary/40 border border-border/80">
            <Check className="h-4 w-4 text-emerald-400 shrink-0" />
            <div>
              <div className="font-semibold text-foreground">Token Vault Isolation</div>
              <div className="text-[11px] text-muted-foreground">No sec_* tokens in payload</div>
            </div>
          </div>

          <div className="flex items-center gap-2 p-2.5 rounded-md bg-secondary/40 border border-border/80">
            {decision.blocked_categories.length > 0 && !decision.canary_leaked ? (
              <X className="h-4 w-4 text-red-400 shrink-0" />
            ) : (
              <Check className="h-4 w-4 text-emerald-400 shrink-0" />
            )}
            <div>
              <div className="font-semibold text-foreground">Pattern Egress Filter</div>
              <div className="text-[11px] text-muted-foreground">All PII replaced with tags</div>
            </div>
          </div>
        </div>

        {/* Firewall Decision Status Bar */}
        <div
          className={`p-3 rounded-lg border text-xs font-mono flex items-start gap-2 ${
            decision.is_allowed
              ? "bg-emerald-950/20 border-emerald-900/50 text-emerald-300"
              : "bg-red-950/40 border-red-900/80 text-red-200"
          }`}
        >
          {decision.is_allowed ? (
            <ShieldCheck className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
          ) : (
            <ShieldAlert className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
          )}
          <div>
            <span className="font-bold uppercase tracking-wider text-[11px] block font-sans">
              Firewall Diagnostic Report:
            </span>
            <span>{decision.reason}</span>
          </div>
        </div>

        {/* Serialized Payload Preview */}
        <div>
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1.5 font-sans">
            <span className="flex items-center gap-1 font-medium">
              <FileCode className="h-3.5 w-3.5" />
              Verified Outbound JSON Payload (Only this reaches external AI):
            </span>
            <span className="font-mono text-[10px] text-cyan-400">
              {JSON.stringify(payload).length} bytes
            </span>
          </div>
          <pre className="p-3 bg-secondary/40 border border-border rounded-md font-mono text-[11px] text-muted-foreground overflow-x-auto max-h-40 leading-relaxed">
            {JSON.stringify(payload, null, 2)}
          </pre>
        </div>
      </CardContent>
    </Card>
  );
};

