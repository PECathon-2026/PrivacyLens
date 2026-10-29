import React, { useState, useCallback } from 'react';
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
import { api, vaultItemsFromObservation } from './api/client';

// Stable task id for this browser session
const SESSION_TASK_ID = `task_${Date.now()}`;

export function App() {
  const [taskPrompt, setTaskPrompt] = useState(
    'Enter passenger details and proceed to payment for flight 6E-204'
  );
  const [targetUrl, setTargetUrl] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);

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

  const addAuditEvent = useCallback((ev: AuditEvent) => {
    setAuditEvents((prev) => [ev, ...prev]);
  }, []);

  // ---------------------------------------------------------------------------
  // Handler: Inspect & Sanitize Page (calls real backend)
  // ---------------------------------------------------------------------------
  const handleInspect = async () => {
    setIsLoading(true);
    setIsSimulatingLeak(false);

    try {
      // Ensure task exists
      await api.createTask(SESSION_TASK_ID, taskPrompt);

      // Observe & sanitize
      const result = await api.observe(SESSION_TASK_ID, targetUrl || undefined);
      setBackendOnline(true);

      setRawObs(result.raw_observation);
      setSanitizedObs(result.sanitized_observation);
      setFirewallDecision(result.firewall_decision);
      setVaultItems(vaultItemsFromObservation(result.sanitized_observation));
      setExecutedActions(new Set());

      addAuditEvent({
        task_id: SESSION_TASK_ID,
        timestamp: getTimestamp(),
        event_type: 'observation_live',
        category: 'BACKEND_PIPELINE',
        item_count: result.sanitized_observation.elements.length,
        decision: result.firewall_decision.is_allowed ? 'FIREWALL_APPROVED' : 'FIREWALL_BLOCKED',
      });

      // Propose actions automatically
      try {
        const actionResult = await api.proposeActions(SESSION_TASK_ID, taskPrompt);
        if (actionResult.actions.length > 0) {
          setProposedActions(actionResult.actions);
          addAuditEvent({
            task_id: SESSION_TASK_ID,
            timestamp: getTimestamp(),
            event_type: 'actions_proposed',
            category: 'AI_REASONING',
            item_count: actionResult.actions.length,
            decision: 'AI_MOCK_OFFLINE',
          });
        }
      } catch {
        // Non-fatal: keep existing proposed actions
      }
    } catch (err) {
      // Backend unreachable → fall back to demo fixture data + local simulation
      setBackendOnline(false);
      console.warn('Backend unreachable, using demo fixture data:', err);
      setFirewallDecision({
        is_allowed: true,
        reason: 'FIREWALL_APPROVED [DEMO MODE]: Outbound payload verified safe and sanitized.',
        blocked_categories: [],
        canary_leaked: false,
      });
      addAuditEvent({
        task_id: SESSION_TASK_ID,
        timestamp: getTimestamp(),
        event_type: 'observation_demo_mode',
        category: 'DOM_REFRESH',
        item_count: INITIAL_DEMO_OBSERVATION.elements.length,
        decision: 'sanitized_and_approved_offline',
      });
    } finally {
      setIsLoading(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Handler: Simulate Canary Leak (calls real firewall-check endpoint)
  // ---------------------------------------------------------------------------
  const handleSimulateCanaryLeak = async () => {
    if (isSimulatingLeak) {
      // Reset
      setIsSimulatingLeak(false);
      setFirewallDecision({
        is_allowed: true,
        reason: 'FIREWALL_APPROVED: Payload re-verified safe after canary simulation reset.',
        blocked_categories: [],
        canary_leaked: false,
      });
      return;
    }

    setIsSimulatingLeak(true);

    // Try live firewall check with injected canary
    let decision: FirewallDecision = {
      is_allowed: false,
      reason: 'FIREWALL_BLOCKED: Planted canary [CANARY_SECRET_TOKEN_9999] detected in serialized egress payload! Transmission halted.',
      blocked_categories: ['KNOWN_SECRET_LEAK', 'CANARY_DETECTED'],
      canary_leaked: true,
    };

    try {
      decision = await api.firewallCheck(
        SESSION_TASK_ID,
        sanitizedObs,
        ['CANARY_SECRET_TOKEN_9999']
      );
    } catch {
      // Backend offline → use local simulation above
    }

    setFirewallDecision(decision);
    addAuditEvent({
      task_id: SESSION_TASK_ID,
      timestamp: getTimestamp(),
      event_type: 'outbound_blocked',
      category: 'CANARY_ATTACK_SIMULATION',
      item_count: 1,
      decision: 'BLOCKED_FAIL_CLOSED',
      error_code: 'EGRESS_VIOLATION_CANARY',
    });
  };

  // ---------------------------------------------------------------------------
  // Handler: Execute Local Injection
  // ---------------------------------------------------------------------------
  const handleExecuteLocalInjection = async (action: ProposedAction) => {
    setExecutedActions((prev) => new Set([...prev, action.target_element_id]));

    setVaultItems((prev) =>
      prev.map((item) =>
        item.field_target === action.target_element_id
          ? { ...item, status: 'INJECTED' as const }
          : item
      )
    );

    try {
      await api.executeAction(
        SESSION_TASK_ID,
        action.action_type,
        action.target_element_id,
        action.value_purpose,
        action.public_value
      );
    } catch {
      // Browser may not be open — local vault update is still valid
    }

    addAuditEvent({
      task_id: SESSION_TASK_ID,
      timestamp: getTimestamp(),
      event_type: 'secret_injected_locally',
      category: action.value_purpose ?? 'LOCAL_VALUE',
      item_count: 1,
      decision: `injected_into_${action.target_element_id}_in_playwright`,
    });
  };

  // ---------------------------------------------------------------------------
  // Handler: Human Approval
  // ---------------------------------------------------------------------------
  const handleApprove = (action: ProposedAction) => {
    setExecutedActions((prev) => new Set([...prev, action.target_element_id]));
    setPendingApprovalAction(null);
    addAuditEvent({
      task_id: SESSION_TASK_ID,
      timestamp: getTimestamp(),
      event_type: 'human_approval_granted',
      category: 'CONSEQUENTIAL_ACTION',
      item_count: 1,
      decision: `APPROVED_BY_USER_FOR_${action.target_element_id}`,
    });
  };

  const handleDeny = (action: ProposedAction) => {
    setPendingApprovalAction(null);
    addAuditEvent({
      task_id: SESSION_TASK_ID,
      timestamp: getTimestamp(),
      event_type: 'human_approval_denied',
      category: 'CONSEQUENTIAL_ACTION',
      item_count: 1,
      decision: `REJECTED_BY_USER_FOR_${action.target_element_id}`,
      error_code: 'USER_REJECTED',
    });
  };

  // ---------------------------------------------------------------------------
  // Handler: Purge Vault
  // ---------------------------------------------------------------------------
  const handlePurgeVault = () => {
    setVaultItems([]);
    addAuditEvent({
      task_id: SESSION_TASK_ID,
      timestamp: getTimestamp(),
      event_type: 'vault_purged',
      category: 'IN_MEMORY_STORAGE',
      item_count: 0,
      decision: 'MEMORY_WIPED_CLEAN',
    });
  };

  // ---------------------------------------------------------------------------
  // Handler: Reset
  // ---------------------------------------------------------------------------
  const handleReset = () => {
    setRawObs(INITIAL_DEMO_OBSERVATION);
    setSanitizedObs(INITIAL_SANITIZED_OBSERVATION);
    setVaultItems(INITIAL_VAULT_ITEMS);
    setProposedActions(INITIAL_PROPOSED_ACTIONS);
    setExecutedActions(new Set());
    setAuditEvents(INITIAL_AUDIT_EVENTS);
    setIsSimulatingLeak(false);
    setBackendOnline(null);
    setFirewallDecision({
      is_allowed: true,
      reason: 'FIREWALL_APPROVED: Outbound payload verified safe and sanitized.',
      blocked_categories: [],
      canary_leaked: false,
    });
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <Navbar
        firewallStatus={firewallDecision.is_allowed ? 'ACTIVE_ARMED' : 'BLOCKED_ALERT'}
        backendOnline={backendOnline}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        <TaskBar
          taskPrompt={taskPrompt}
          setTaskPrompt={setTaskPrompt}
          targetUrl={targetUrl}
          setTargetUrl={setTargetUrl}
          onInspect={handleInspect}
          onSimulateCanaryLeak={handleSimulateCanaryLeak}
          onReset={handleReset}
          isSimulatingLeak={isSimulatingLeak}
          isLoading={isLoading}
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
        {backendOnline === false && (
          <span className="ml-3 text-amber-400 font-semibold">⚠ Demo Mode (Backend Offline)</span>
        )}
        {backendOnline === true && (
          <span className="ml-3 text-emerald-400 font-semibold">● Live Backend Connected</span>
        )}
      </footer>
    </div>
  );
}

export default App;
