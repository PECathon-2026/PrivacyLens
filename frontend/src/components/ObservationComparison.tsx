import React, { useState } from 'react';
import { Shield, Eye, Lock, FileText, CheckCircle2, AlertOctagon, Terminal } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { PageObservation, SanitizedObservation } from '@/types';

interface ObservationComparisonProps {
  rawObs: PageObservation;
  sanitizedObs: SanitizedObservation;
}

export const ObservationComparison: React.FC<ObservationComparisonProps> = ({
  rawObs,
  sanitizedObs,
}) => {
  const [activeTab, setActiveTab] = useState<'comparison' | 'sanitizedText' | 'rawDom'>('comparison');

  const getCategoryBadge = (placeholder: string) => {
    if (placeholder.includes('CREDIT_CARD')) return <Badge variant="destructive">CREDIT_CARD</Badge>;
    if (placeholder.includes('EMAIL')) return <Badge variant="cyan">EMAIL</Badge>;
    if (placeholder.includes('PHONE')) return <Badge variant="warning">PHONE</Badge>;
    if (placeholder.includes('PAN')) return <Badge variant="default">PAN_CARD</Badge>;
    if (placeholder.includes('AADHAAR')) return <Badge variant="default">AADHAAR</Badge>;
    if (placeholder.includes('PASSWORD')) return <Badge variant="destructive">PASSWORD</Badge>;
    return <Badge variant="secondary">PUBLIC_CONTEXT</Badge>;
  };

  return (
    <Card className="border-border shadow-md">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <div>
          <CardTitle className="text-base font-semibold">
            <Shield className="h-4 w-4 text-cyan-400" />
            Local Observation & PrivacyLens Transformation
          </CardTitle>
          <CardDescription>
            Compute what is sensitive locally. Replace PII with semantic placeholders before model egress.
          </CardDescription>
        </div>

        {/* Redaction Summary Badges */}
        <div className="flex flex-wrap items-center gap-1.5">
          {Object.entries(sanitizedObs.redaction_summary).map(([category, count]) => (
            <span
              key={category}
              className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-secondary border border-border text-foreground flex items-center gap-1"
            >
              <span className="font-semibold text-cyan-400">{count}</span>
              <span className="text-muted-foreground">{category}</span>
            </span>
          ))}
        </div>
      </CardHeader>

      <CardContent>
        <Tabs value={activeTab} onValueChange={(val) => setActiveTab(val as any)}>
          <TabsList className="grid w-full grid-cols-3 max-w-md">
            <TabsTrigger value="comparison" className="gap-1.5">
              <Eye className="h-3.5 w-3.5" />
              Side-by-Side Diff
            </TabsTrigger>
            <TabsTrigger value="sanitizedText" className="gap-1.5">
              <FileText className="h-3.5 w-3.5" />
              Sanitized Text Context
            </TabsTrigger>
            <TabsTrigger value="rawDom" className="gap-1.5">
              <Terminal className="h-3.5 w-3.5" />
              Raw Local DOM
            </TabsTrigger>
          </TabsList>

          {/* TAB 1: SIDE BY SIDE COMPARISON */}
          <TabsContent value="comparison" className="space-y-3 pt-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="bg-red-950/20 border border-red-900/40 rounded-lg p-3">
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-red-900/30">
                  <div className="flex items-center gap-1.5 text-red-400 font-semibold uppercase tracking-wider text-[11px]">
                    <AlertOctagon className="h-3.5 w-3.5" />
                    Local Browser DOM (Raw Unsanitized)
                  </div>
                  <span className="text-[10px] text-red-400/80 font-mono">Kept Local Only</span>
                </div>

                <div className="space-y-2">
                  {rawObs.elements.map((elem) => (
                    <div
                      key={elem.element_id}
                      className="p-2.5 rounded bg-background/80 border border-border/60 font-mono"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-muted-foreground text-[10px]">{elem.element_id} ({elem.input_type || elem.role})</span>
                        <span className="text-foreground font-sans font-medium text-xs">{elem.label}</span>
                      </div>
                      <div className="text-xs text-red-300 font-medium break-all">
                        {elem.value ? elem.value : <span className="text-muted-foreground italic">(empty button/field)</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="bg-cyan-950/20 border border-cyan-800/40 rounded-lg p-3">
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-cyan-800/30">
                  <div className="flex items-center gap-1.5 text-cyan-400 font-semibold uppercase tracking-wider text-[11px]">
                    <CheckCircle2 className="h-3.5 w-3.5 text-cyan-400" />
                    PrivacyLens Egress Payload (AI Bound)
                  </div>
                  <span className="text-[10px] text-cyan-300 font-mono">Safe for External LLM</span>
                </div>

                <div className="space-y-2">
                  {sanitizedObs.elements.map((elem) => (
                    <div
                      key={elem.element_id}
                      className="p-2.5 rounded bg-background/80 border border-cyan-900/30 font-mono"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-cyan-400 text-[10px]">{elem.element_id} ({elem.input_type || elem.role})</span>
                        {getCategoryBadge(elem.value)}
                      </div>
                      <div className="text-xs font-semibold break-all text-cyan-200">
                        {elem.value ? (
                          elem.value.startsWith('[REDACTED') ? (
                            <span className="text-cyan-400 bg-cyan-950/60 px-1.5 py-0.5 rounded border border-cyan-800/60">
                              {elem.value}
                            </span>
                          ) : (
                            <span className="text-foreground font-normal">{elem.value}</span>
                          )
                        ) : (
                          <span className="text-muted-foreground italic">{elem.label}</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </TabsContent>

          {/* TAB 2: SANITIZED TEXT */}
          <TabsContent value="sanitizedText">
            <div className="bg-secondary/40 border border-border rounded-lg p-4 font-mono text-xs leading-relaxed text-foreground/90 whitespace-pre-wrap">
              <div className="flex items-center gap-2 mb-3 text-cyan-400 font-semibold uppercase tracking-wider text-[11px] font-sans">
                <Lock className="h-3.5 w-3.5" />
                Sanitized Visible Page Context (Natural Language Egress)
              </div>
              <p className="p-3 bg-background/70 border border-border/80 rounded-md">
                {sanitizedObs.sanitized_text}
              </p>
            </div>
          </TabsContent>

          {/* TAB 3: RAW DOM JSON */}
          <TabsContent value="rawDom">
            <div className="bg-secondary/40 border border-border rounded-lg p-3 font-mono text-xs overflow-x-auto max-h-72">
              <pre className="text-muted-foreground text-[11px]">
                {JSON.stringify(rawObs, null, 2)}
              </pre>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
};
