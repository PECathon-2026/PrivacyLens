import React, { useState } from 'react';
import { Bot, CheckCircle, ArrowRight, ShieldAlert, Key, Sparkles } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ProposedAction } from '@/types';

interface ActionExecutorCardProps {
  proposedActions: ProposedAction[];
  onRequestApproval: (action: ProposedAction) => void;
  onExecuteLocalInjection: (action: ProposedAction) => void;
  executedActions: Set<string>;
}

export const ActionExecutorCard: React.FC<ActionExecutorCardProps> = ({
  proposedActions,
  onRequestApproval,
  onExecuteLocalInjection,
  executedActions,
}) => {
  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold">
            <Bot className="h-5 w-5 text-cyan-400" />
            AI Reasoning & Local Action Validator
          </CardTitle>
          <Badge variant="cyan" className="font-mono text-[10px]">
            STRUCTURED REASONING PLANE
          </Badge>
        </div>
        <CardDescription>
          External AI reasons over sanitized placeholders and emits structured actions. The Local Action Executor validates and injects secrets directly into Playwright.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-3">
        {proposedActions.map((action, idx) => {
          const isExecuted = executedActions.has(action.target_element_id);
          const isConsequential = action.action_type === 'request_approval' || action.target_element_id.includes('submit');

          return (
            <div
              key={idx}
              className={`p-3.5 rounded-lg border transition-all ${
                isExecuted
                  ? "bg-secondary/20 border-border/40 opacity-75"
                  : isConsequential
                  ? "bg-amber-950/20 border-amber-900/50"
                  : "bg-secondary/40 border-border"
              }`}
            >
              <div className="flex items-start justify-between gap-3 mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs px-2 py-0.5 rounded bg-background border border-border text-cyan-400 font-semibold">
                    {action.action_type}
                  </span>
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                  <span className="font-mono text-xs text-foreground bg-secondary px-2 py-0.5 rounded">
                    target: {action.target_element_id}
                  </span>
                  {action.value_purpose && (
                    <Badge variant="outline" className="text-[10px] uppercase">
                      purpose: {action.value_purpose}
                    </Badge>
                  )}
                </div>

                {isExecuted ? (
                  <Badge variant="success" className="gap-1 text-[10px]">
                    <CheckCircle className="h-3 w-3" />
                    EXECUTED LOCALLY
                  </Badge>
                ) : isConsequential ? (
                  <Badge variant="warning" className="gap-1 text-[10px]">
                    <ShieldAlert className="h-3 w-3" />
                    APPROVAL REQUIRED
                  </Badge>
                ) : (
                  <Badge variant="outline" className="text-[10px]">
                    VALIDATED BY POLICY
                  </Badge>
                )}
              </div>

              <p className="text-xs text-muted-foreground mb-3 font-sans">
                {action.reasoning}
              </p>

              {/* Execution Actions */}
              <div className="flex items-center justify-between pt-2 border-t border-border/40">
                <div className="text-[11px] text-muted-foreground font-mono flex items-center gap-1.5">
                  <Key className="h-3 w-3 text-cyan-400" />
                  <span>
                    {action.action_type === 'fill_local_value'
                      ? "Resolves real secret from local vault -> types in Playwright (AI never sees value)"
                      : "Irreversible state mutation requires user approval"}
                  </span>
                </div>

                {!isExecuted && (
                  <div>
                    {isConsequential ? (
                      <Button
                        size="sm"
                        variant="destructive"
                        className="text-xs gap-1.5 h-7"
                        onClick={() => onRequestApproval(action)}
                      >
                        <ShieldAlert className="h-3.5 w-3.5" />
                        Review & Authorize
                      </Button>
                    ) : (
                      <Button
                        size="sm"
                        variant="secondary"
                        className="text-xs gap-1.5 h-7 border border-cyan-800/60 hover:border-cyan-500"
                        onClick={() => onExecuteLocalInjection(action)}
                      >
                        <Sparkles className="h-3.5 w-3.5 text-cyan-400" />
                        Execute Local Injection
                      </Button>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
};
