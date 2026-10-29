import React from 'react';
import { Lock, Trash2, Shield, DatabaseZap } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { SecretVaultItem } from '@/types';

interface LocalVaultCardProps {
  vaultItems: SecretVaultItem[];
  onPurgeVault: () => void;
}

export const LocalVaultCard: React.FC<LocalVaultCardProps> = ({
  vaultItems,
  onPurgeVault,
}) => {
  return (
    <Card className="border-border">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base font-semibold">
            <Lock className="h-4 w-4 text-emerald-400" />
            Local Ephemeral Session Vault
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="success" className="text-[10px] gap-1">
              <DatabaseZap className="h-3 w-3" />
              RAM ONLY (0 DISK WRITES)
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-muted-foreground hover:text-red-400"
              onClick={onPurgeVault}
              title="Purge all active secrets for this session"
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" />
              Purge
            </Button>
          </div>
        </div>
        <CardDescription>
          Original sensitive values are kept solely in process memory for the task lifetime and resolved only by local Playwright executors.
        </CardDescription>
      </CardHeader>

      <CardContent>
        {vaultItems.length === 0 ? (
          <div className="text-center py-6 text-xs text-muted-foreground">
            Vault is empty. Run an inspection to populate task-scoped secrets.
          </div>
        ) : (
          <div className="space-y-2">
            {vaultItems.map((item, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2.5 rounded-md bg-secondary/30 border border-border/60 text-xs font-mono"
              >
                <div className="flex items-center gap-2.5">
                  <span className="h-2 w-2 rounded-full bg-emerald-400" />
                  <span className="text-cyan-400 font-semibold">{item.token}</span>
                  <span className="text-muted-foreground text-[11px]">→ {item.field_target}</span>
                </div>

                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="text-[10px]">
                    {item.category}
                  </Badge>
                  <span className="text-[10px] text-emerald-400 font-medium font-sans">
                    {item.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
