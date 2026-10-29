import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { TaskBar } from './components/TaskBar';
import { ObservationComparison } from './components/ObservationComparison';
import { OutboundFirewallCard } from './components/OutboundFirewallCard';
import { ActionExecutorCard } from './components/ActionExecutorCard';
import { LocalVaultCard } from './components/LocalVaultCard';
import { AuditFeed } from './components/AuditFeed';
import { ApprovalModal } from './components/ApprovalModal';
import {
  INITIAL_DEMO_OBSERVATION,
  INITIAL_SANITIZED_OBSERVATION,
  INITIAL_VAULT_ITEMS,
  INITIAL_PROPOSED_ACTIONS,
  INITIAL_AUDIT_EVENTS,
} from './lib/demoData';
import {
  PageObservation,
  SanitizedObservation,
  FirewallDecision,
  ProposedAction,
  AuditEvent,
  SecretVaultItem,
} from './types';

export function App() {
  const [taskPrompt, setTaskPrompt] = useState(
    'Enter passenger details and proceed to payment for flight 6E-204'
  );
  const [rawObs, setRawObs] = useState<PageObservation>(INITIAL_DEMO_OBSERVATION);
  const [sanitizedObs, setSanitizedObs] = useState<SanitizedObservation>(
    INITIAL_SANITIZED_OBSERVATION
  );
  const [vaultItems, setVaultItems] = useState<SecretVaultItem[]>(INITIAL_VAULT_ITEMS);
  const [proposedActions, setProposedActions] = useState<ProposedAction[]>(
    INITIAL_PROPOSED_ACTIONS
  );
  const [executedActions, setExecutedActions] = useState<Set<string>>(new Set());
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>(INITIAL_AUDIT_EVENTS);
  const [pendingApprovalAction, setPendingApprovalAction] = useState<ProposedAction | null>(null);

  // Outbound Firewall State
  const [isSimulatingLeak, setIsSimulatingLeak] = useState(false);
  const [firewallDecision, setFirewallDecision] = useState<FirewallDecision>({
    is_allowed: true,
    reason: 'FIREWALL_APPROVED: Outbound payload verified safe. All PII substituted with semantic placeholders.',
    blocked_categories: [],
    canary_leaked: false,
  });

  const getTimestamp = () => new Date().toLocaleTimeString();

  // Handler: Inspect & Sanitize Page
  const handleInspect = () => {
    setIsSimulatingLeak(false);
    setFirewallDecision({
      is_allowed: true,
      reason: 'FIREWALL_APPROVED: Outbound payload verified safe and sanitized.',
      blocked_categories: [],
      canary_leaked: false,
    });

    const newEvent: AuditEvent = {
      task_id: rawObs.task_id,
      timestamp: getTimestamp(),
      event_type: 'observation_reinspected',
      category: 'DOM_REFRESH',
      item_count: rawObs.elements.length,
      decision: 'sanitized_and_approved',
    };
    setAuditEvents((prev) => [newEvent, ...prev]);
  };

  // Handler: Simulate Canary Leak (Tests Fail-Closed Firewall)
  const handleSimulateCanaryLeak = () => {
    if (!isSimulatingLeak) {
      setIsSimulatingLeak(true);
      setFirewallDecision({
        is_allowed: false,
        reason: 'FIREWALL_BLOCKED: Planted canary [CANARY_SECRET_TOKEN_9999] detected in serialized egress payload! Transmission halted.',
        blocked_categories: ['KNOWN_SECRET_LEAK', 'CANARY_DETECTED'],
        canary_leaked: true,
      });

      const blockEvent: AuditEvent = {
        task_id: rawObs.task_id,
        timestamp: getTimestamp(),
        event_type: 'outbound_blocked',
        category: 'CANARY_ATTACK_SIMULATION',
        item_count: 1,
        decision: 'BLOCKED_FAIL_CLOSED',
        error_code: 'EGRESS_VIOLATION_CANARY',
      };
      setAuditEvents((prev) => [blockEvent, ...prev]);
    } else {
      handleInspect();
    }
  };

  // Handler: Execute Local Injection
  const handleExecuteLocalInjection = (action: ProposedAction) => {
    setExecutedActions((prev) => new Set([...prev, action.target_element_id]));

    // Update vault status to injected
    setVaultItems((prev) =>
      prev.map((item) =>
        item.field_target === action.target_element_id
          ? { ...item, status: 'INJECTED' }
          : item
      )
    );

    const auditEv: AuditEvent = {
      task_id: rawObs.task_id,
      timestamp: getTimestamp(),
      event_type: 'secret_injected_locally',
      category: action.value_purpose || 'LOCAL_VALUE',
      item_count: 1,
      decision: `injected_into_${action.target_element_id}_in_playwright`,
    };
    setAuditEvents((prev) => [auditEv, ...prev]);
  };

  // Handler: Human Approval Granted
  const handleApprove = (action: ProposedAction) => {
    setExecutedActions((prev) => new Set([...prev, action.target_element_id]));
    setPendingApprovalAction(null);

    const auditEv: AuditEvent = {
      task_id: rawObs.task_id,
      timestamp: getTimestamp(),
      event_type: 'human_approval_granted',
      category: 'CONSEQUENTIAL_ACTION',
      item_count: 1,
      decision: `APPROVED_BY_USER_FOR_${action.target_element_id}`,
    };
    setAuditEvents((prev) => [auditEv, ...prev]);
  };

  // Handler: Human Approval Denied
  const handleDeny = (action: ProposedAction) => {
    setPendingApprovalAction(null);

    const auditEv: AuditEvent = {
      task_id: rawObs.task_id,
      timestamp: getTimestamp(),
      event_type: 'human_approval_denied',
      category: 'CONSEQUENTIAL_ACTION',
      item_count: 1,
      decision: `REJECTED_BY_USER_FOR_${action.target_element_id}`,
      error_code: 'USER_REJECTED',
    };
    setAuditEvents((prev) => [auditEv, ...prev]);
  };

  // Handler: Purge Vault
  const handlePurgeVault = () => {
    setVaultItems([]);
    const auditEv: AuditEvent = {
      task_id: rawObs.task_id,
      timestamp: getTimestamp(),
      event_type: 'vault_purged',
      category: 'IN_MEMORY_STORAGE',
      item_count: 0,
      decision: 'MEMORY_WIPED_CLEAN',
    };
    setAuditEvents((prev) => [auditEv, ...prev]);
  };

  // Handler: Reset to baseline
  const handleReset = () => {
    setRawObs(INITIAL_DEMO_OBSERVATION);
    setSanitizedObs(INITIAL_SANITIZED_OBSERVATION);
    setVaultItems(INITIAL_VAULT_ITEMS);
    setProposedActions(INITIAL_PROPOSED_ACTIONS);
    setExecutedActions(new Set());
    setAuditEvents(INITIAL_AUDIT_EVENTS);
    setIsSimulatingLeak(false);
    setFirewallDecision({
      is_allowed: true,
      reason: 'FIREWALL_APPROVED: Outbound payload verified safe and sanitized.',
      blocked_categories: [],
      canary_leaked: false,
    });
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Navbar firewallStatus={firewallDecision.is_allowed ? 'ACTIVE_ARMED' : 'BLOCKED_ALERT'} />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        <TaskBar
          taskPrompt={taskPrompt}
          setTaskPrompt={setTaskPrompt}
          onInspect={handleInspect}
          onSimulateCanaryLeak={handleSimulateCanaryLeak}
          onReset={handleReset}
          isSimulatingLeak={isSimulatingLeak}
        />

        {/* TOP SECTION: Observation Comparison (Before & After) */}
        <ObservationComparison rawObs={rawObs} sanitizedObs={sanitizedObs} />

        {/* MIDDLE SECTION: Outbound Firewall & AI Reasoning Plane */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <OutboundFirewallCard decision={firewallDecision} payload={sanitizedObs} />
          <ActionExecutorCard
            proposedActions={proposedActions}
            onRequestApproval={(action) => setPendingApprovalAction(action)}
            onExecuteLocalInjection={handleExecuteLocalInjection}
            executedActions={executedActions}
          />
        </div>

        {/* BOTTOM SECTION: Local In-Memory Vault & Non-Sensitive Audit Trail */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <LocalVaultCard vaultItems={vaultItems} onPurgeVault={handlePurgeVault} />
          <AuditFeed events={auditEvents} />
        </div>
      </main>

      <ApprovalModal
        action={pendingApprovalAction}
        onApprove={handleApprove}
        onDeny={handleDeny}
        onClose={() => setPendingApprovalAction(null)}
      />

      <footer className="border-t border-border/60 py-4 px-6 text-center text-xs text-muted-foreground bg-card/30">
        PrivacyLens — Hackathon PS-004 Prototype • Dual-Plane Architecture • Zero Cloud PII Leakage
      </footer>
    </div>
  );
}

export default App;
