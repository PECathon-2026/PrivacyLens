import React from 'react';
import { History, ShieldCheck, CheckCircle2, ShieldAlert } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { AuditEvent } from '@/types';

interface AuditFeedProps {
  events: AuditEvent[];
}

export const AuditFeed: React.FC<AuditFeedProps> = ({ events }) => {
  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold">
            <History className="h-4 w-4 text-cyan-400" />
            Non-Sensitive Audit Trail
          </CardTitle>
          <Badge variant="outline" className="text-[10px] font-mono">
            VERIFIED NO RAW SECRETS IN LOGS
          </Badge>
        </div>
        <CardDescription>
          Immutable operational event log recording decisions and metadata without storing raw sensitive strings.
        </CardDescription>
      </CardHeader>

      <CardContent>
        <div className="space-y-2.5 max-h-56 overflow-y-auto pr-1">
          {events.map((ev, idx) => {
            const isBlocked = ev.decision.includes('BLOCKED');

            return (
              <div
                key={idx}
                className="flex items-start justify-between p-2 rounded-md bg-secondary/30 border border-border/50 text-xs"
              >
                <div className="flex items-start gap-2.5">
                  {isBlocked ? (
                    <ShieldAlert className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
                  ) : (
                    <ShieldCheck className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-foreground font-mono text-[11px]">
                        {ev.event_type}
                      </span>
                      {ev.category && (
                        <span className="text-[10px] text-muted-foreground px-1.5 py-0.2 rounded bg-secondary">
                          {ev.category}
                        </span>
                      )}
                    </div>
                    <div className="text-[11px] text-muted-foreground mt-0.5 font-mono">
                      decision: <span className={isBlocked ? "text-red-400 font-semibold" : "text-emerald-400"}>{ev.decision}</span>
                      {ev.item_count > 0 && <span> ({ev.item_count} items)</span>}
                    </div>
                  </div>
                </div>

                <span className="text-[10px] text-muted-foreground/80 font-mono shrink-0">
                  {ev.timestamp}
                </span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
};

