export interface PageElement {
  element_id: string;
  role: string;
  label: string;
  input_type: string;
  name: string;
  placeholder: string;
  value: string;
  visible: boolean;
  enabled: boolean;
}

export interface PageObservation {
  task_id: string;
  url: string;
  title: string;
  visible_text: string;
  elements: PageElement[];
}

export interface SanitizedPageElement {
  element_id: string;
  role: string;
  label: string;
  input_type: string;
  name: string;
  placeholder: string;
  value: string;
  visible: boolean;
  enabled: boolean;
}

export interface SanitizedObservation {
  task_id: string;
  url: string;
  title: string;
  sanitized_text: string;
  elements: SanitizedPageElement[];
  redaction_summary: Record<string, number>;
}

export interface FirewallDecision {
  is_allowed: boolean;
  reason: string;
  blocked_categories: string[];
  canary_leaked: boolean;
}

export interface ProposedAction {
  action_type: 'click' | 'fill_local_value' | 'fill_public_value' | 'select_option' | 'request_approval';
  target_element_id: string;
  value_purpose?: string;
  public_value?: string;
  reasoning: string;
}

export interface AuditEvent {
  task_id: string;
  timestamp: string;
  event_type: string;
  category: string;
  item_count: number;
  decision: string;
  error_code?: string | null;
}

export interface SecretVaultItem {
  token: string;
  category: string;
  field_target: string;
  status: 'LOCKED_IN_MEMORY' | 'INJECTED';
}

