import React from 'react';
import { ShieldAlert, AlertTriangle, Check, X, Lock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ProposedAction } from '@/types';

interface ApprovalModalProps {
  action: ProposedAction | null;
  onApprove: (action: ProposedAction) => void;
  onDeny: (action: ProposedAction) => void;
  onClose: () => void;
}

export const ApprovalModal: React.FC<ApprovalModalProps> = ({
  action,
  onApprove,
  onDeny,
  onClose,
}) => {
  if (!action) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in">
      <div className="bg-card border border-amber-500/40 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-full bg-amber-500/20 border border-amber-500/40 flex items-center justify-center text-amber-400 shrink-0">
            <ShieldAlert className="h-5 w-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-foreground">
              Human-in-the-Loop Authorization Required
            </h3>
            <p className="text-xs text-muted-foreground">
              PrivacyLens Policy Enforcement: Consequential action flagged as irreversible.
            </p>
          </div>
        </div>

        <div className="bg-secondary/40 border border-border rounded-lg p-4 space-y-2.5 text-xs font-mono">
          <div className="flex items-center justify-between pb-2 border-b border-border/50">
            <span className="text-muted-foreground">Action Type:</span>
            <Badge variant="warning">{action.action_type}</Badge>
          </div>

          <div className="flex items-center justify-between pb-2 border-b border-border/50">
            <span className="text-muted-foreground">Target Selector:</span>
            <span className="text-cyan-400 font-semibold">{action.target_element_id}</span>
          </div>

          {action.public_value && (
            <div className="flex items-center justify-between pb-2 border-b border-border/50">
              <span className="text-muted-foreground">Authorization Value:</span>
              <span className="text-foreground font-bold">{action.public_value}</span>
            </div>
          )}

          <div className="pt-1">
            <span className="text-muted-foreground block mb-1">Model Reasoning:</span>
            <p className="font-sans text-xs text-muted-foreground/90 bg-background/60 p-2.5 rounded border border-border/40">
              {action.reasoning}
            </p>
          </div>
        </div>

        <div className="p-3 bg-amber-950/20 border border-amber-900/40 rounded-lg flex items-start gap-2 text-xs text-amber-200">
          <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          <span>
            Approving this action will instruct local Playwright to trigger the button and dispatch the booking on the website. No raw secrets are revealed to the AI.
          </span>
        </div>

        <div className="flex items-center justify-end gap-2.5 pt-2">
          <Button variant="outline" size="sm" onClick={() => onDeny(action)} className="gap-1.5 text-xs">
            <X className="h-3.5 w-3.5" />
            Deny Action
          </Button>
          <Button variant="destructive" size="sm" onClick={() => onApprove(action)} className="gap-1.5 text-xs bg-amber-600 hover:bg-amber-700 text-white">
            <Check className="h-3.5 w-3.5" />
            Approve & Execute via Playwright
          </Button>
        </div>
      </div>
    </div>
  );
};

