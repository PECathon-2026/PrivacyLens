/**
 * PrivacyLens API Client
 * Typed fetch wrappers for all FastAPI gateway endpoints.
 * Falls back to demo fixture data when the backend is unreachable.
 */

import type {
  PageObservation,
  SanitizedObservation,
  FirewallDecision,
  ProposedAction,
  AuditEvent,
  SecretVaultItem,
} from '../types';

const BASE_URL = import.meta.env.VITE_API_URL ?? '';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`POST ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`GET ${path} → ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Response shapes (mirror Python response dicts)
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  gateway: string;
  version: string;
  mode: string;
  firewall: string;
}

export interface CreateTaskResponse {
  task_id: string;
  status: string;
}

export interface ObserveResponse {
  task_id: string;
  raw_observation: PageObservation;
  sanitized_observation: SanitizedObservation;
  firewall_decision: FirewallDecision;
  vault_secret_count: number;
}

export interface ProposeActionsResponse {
  actions: ProposedAction[];
}

export interface ExecuteActionResponse {
  success: boolean;
  action_type: string;
  target_element_id: string;
  note?: string;
}

export interface AuditResponse {
  task_id: string;
  events: AuditEvent[];
}

// ---------------------------------------------------------------------------
// Derived helpers for the UI
// ---------------------------------------------------------------------------

/** Derive vault items from a sanitized observation's redaction summary + elements */
export function vaultItemsFromObservation(
  obs: SanitizedObservation
): SecretVaultItem[] {
  return obs.elements
    .filter((el) => el.value.startsWith('[REDACTED:'))
    .map((el) => {
      const match = el.value.match(/\[REDACTED:([A-Z_]+)\]/);
      const category = match ? match[1] : 'UNKNOWN';
      return {
        token: `sec_${el.element_id.replace('el_', '')}`,
        category,
        field_target: el.element_id,
        status: 'LOCKED_IN_MEMORY' as const,
      };
    });
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export const api = {
  /** Check that the local gateway is reachable. */
  health(): Promise<HealthResponse> {
    return get<HealthResponse>('/health');
  },

  /** Create a new task session. */
  createTask(taskId: string, taskLabel?: string): Promise<CreateTaskResponse> {
    return post<CreateTaskResponse>('/api/tasks', {
      task_id: taskId,
      task_label: taskLabel ?? 'PrivacyLens Session',
    });
  },

  /**
   * Extract the demo page DOM, detect sensitive data, sanitize it, and run
   * the outbound firewall. Returns raw + sanitized observations plus the
   * initial firewall decision.
   */
  observe(taskId: string, url?: string): Promise<ObserveResponse> {
    return post<ObserveResponse>(`/api/tasks/${taskId}/observe`, {
      url: url ?? null,
      use_sample_page: !url,
    });
  },

  /**
   * Check an outbound payload through the privacy firewall.
   * Optionally inject canary tokens to test fail-closed behavior.
   */
  firewallCheck(
    taskId: string,
    sanitizedObservation: SanitizedObservation,
    canaries?: string[]
  ): Promise<FirewallDecision> {
    return post<FirewallDecision>(`/api/tasks/${taskId}/firewall-check`, {
      sanitized_observation: sanitizedObservation,
      canaries: canaries ?? [],
    });
  },

  /**
   * Send the sanitized page context to the AI reasoning plane (or offline
   * mock) and receive structured action proposals.
   */
  proposeActions(taskId: string, taskPrompt: string): Promise<ProposeActionsResponse> {
    return post<ProposeActionsResponse>(`/api/tasks/${taskId}/propose-action`, {
      task_prompt: taskPrompt,
    });
  },

  /**
   * Execute a single action via Playwright.
   * For 'fill_local_value' actions the backend resolves the real secret from
   * its in-memory vault and fills the form directly — the value never crosses
   * the API boundary.
   */
  executeAction(
    taskId: string,
    actionType: string,
    targetElementId: string,
    valuePurpose?: string,
    publicValue?: string
  ): Promise<ExecuteActionResponse> {
    return post<ExecuteActionResponse>(`/api/tasks/${taskId}/execute-action`, {
      action_type: actionType,
      target_element_id: targetElementId,
      value_purpose: valuePurpose,
      public_value: publicValue,
    });
  },

  /** Fetch the non-sensitive audit timeline for a task. */
  getAudit(taskId: string): Promise<AuditResponse> {
    return get<AuditResponse>(`/api/tasks/${taskId}/audit`);
  },
};
