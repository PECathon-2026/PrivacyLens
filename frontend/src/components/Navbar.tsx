import React from 'react';
import { ShieldCheck, EyeOff, Lock, Cpu } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface NavbarProps {
  firewallStatus: 'ACTIVE_ARMED' | 'BLOCKED_ALERT';
}

export const Navbar: React.FC<NavbarProps> = ({ firewallStatus }) => {
  return (
    <header className="border-b border-border bg-card/60 backdrop-blur-md sticky top-0 z-50 px-6 py-3.5">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 ring-1 ring-cyan-400/30">
            <ShieldCheck className="h-6 w-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-cyan-300 via-sky-200 to-white bg-clip-text text-transparent">
                PrivacyLens
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-primary/20 text-cyan-300 font-mono font-medium border border-primary/30">
                v1.0 MVP
              </span>
            </div>
            <p className="text-xs text-muted-foreground flex items-center gap-1.5">
              <span>Privacy-Preserving AI Browser Agent</span>
              <span className="inline-block w-1 h-1 rounded-full bg-muted-foreground/60"></span>
              <span className="italic text-cyan-400/80">"Compute locally. Reason on sanitized data."</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-md bg-secondary/60 border border-border/80 text-xs text-muted-foreground">
            <Cpu className="h-3.5 w-3.5 text-cyan-400" />
            <span>AI Reasoning:</span>
            <span className="text-foreground font-medium">Model-Agnostic / Offline Mock</span>
          </div>

          <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-md bg-secondary/60 border border-border/80 text-xs text-muted-foreground">
            <Lock className="h-3.5 w-3.5 text-emerald-400" />
            <span>Vault:</span>
            <span className="text-emerald-400 font-medium">In-Memory Ephemeral</span>
          </div>

          {firewallStatus === 'ACTIVE_ARMED' ? (
            <Badge variant="success" className="px-3 py-1 text-xs gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              FIREWALL: ARMED (FAIL-CLOSED)
            </Badge>
          ) : (
            <Badge variant="destructive" className="px-3 py-1 text-xs gap-1.5 animate-bounce">
              <EyeOff className="h-3.5 w-3.5" />
              FIREWALL BLOCKED: CANARY DETECTED
            </Badge>
          )}
        </div>
      </div>
    </header>
  );
};
