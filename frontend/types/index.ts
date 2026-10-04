/** Shared domain types mirroring the backend Pydantic schemas. */

export type Role = "owner" | "admin" | "editor" | "viewer" | "member";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  is_superuser: boolean;
  mfa_enabled: boolean;
  avatar_url: string | null;
  org_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  owner_id: string;
  plan: string;
  settings: Record<string, unknown> | null;
  member_count: number | null;
  created_at: string;
  updated_at: string;
}

export interface Member {
  id: string;
  workspace_id: string;
  user_id: string;
  role: Role;
  email: string | null;
  full_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface Notebook {
  id: string;
  workspace_id: string;
  title: string;
  description: string | null;
  emoji: string | null;
  color: string | null;
  owner_id: string;
  folder_id: string | null;
  is_archived: boolean;
  document_count: number | null;
  conversation_count: number | null;
  created_at: string;
  updated_at: string;
}

export type DocumentStatus =
  | "pending"
  | "uploaded"
  | "parsing"
  | "ocr"
  | "chunking"
  | "embedding"
  | "ready"
  | "failed";

export interface SourceDocument {
  id: string;
  workspace_id: string;
  notebook_id: string;
  uploaded_by: string;
  title: string;
  source: string;
  source_uri: string | null;
  mime_type: string;
  size_bytes: number;
  status: DocumentStatus;
  pages: number | null;
  language: string | null;
  error: string | null;
  progress: number | null;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: string;
  workspace_id: string;
  notebook_id: string;
  user_id: string;
  title: string;
  agent: string;
  pinned: boolean;
  last_message_at: string | null;
  message_count: number | null;
  created_at: string;
  updated_at: string;
}

export type MessageRole = "system" | "user" | "assistant" | "tool";

export interface CitationRef {
  id: number;
  document_id: string;
  document_title: string;
  chunk_id: string | null;
  page: number | null;
  section: string | null;
  snippet: string;
  score: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: MessageRole;
  content: string;
  citations: CitationRef[] | null;
  tool_calls: unknown[] | null;
  model: string | null;
  latency_ms: number | null;
  created_at: string;
  updated_at: string;
}

export interface SearchHit {
  document_id: string;
  document_title: string;
  chunk_id: string;
  page: number | null;
  section: string | null;
  text: string;
  score: number;
}

export type SearchMode = "semantic" | "keyword" | "hybrid" | "graph" | "memory";

export interface ChatStreamEvent {
  event: "sources" | "delta" | "done" | "close";
  data: any;
}

// ── Studio artifacts ─────────────────────────────────────────
export type ArtifactKind =
  | "custom"
  | "audio_overview"
  | "slide_deck"
  | "mind_map"
  | "report"
  | "flashcards"
  | "quiz"
  | "infographic"
  | "data_table";

export type ArtifactStatus = "pending" | "generating" | "ready" | "failed";

export interface KindInfo {
  kind: ArtifactKind;
  label: string;
  emoji: string;
  description: string;
  supports_count: boolean;
  default_count: number | null;
  count_label: string | null;
}

export interface ArtifactSummary {
  id: string;
  notebook_id: string;
  kind: ArtifactKind;
  status: ArtifactStatus;
  title: string;
  prompt: string | null;
  model: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export interface Artifact extends ArtifactSummary {
  content: ArtifactContent | null;
  citations: CitationRef[] | null;
  source_document_ids: string[] | null;
  tokens_used: number;
  took_ms: number;
}

// ── Per-kind content shapes (mirror app/contexts/artifact/schemas.py) ──
export interface CustomContent {
  format: "markdown";
  body: string;
}
export interface DialogueTurn {
  speaker: string;
  text: string;
}
export interface AudioOverviewContent {
  title: string;
  description: string;
  host_a: string;
  host_b: string;
  est_seconds: number;
  turns: DialogueTurn[];
}
export interface Slide {
  title: string;
  bullets: string[];
  notes: string;
}
export interface SlideDeckContent {
  title: string;
  subtitle: string;
  slides: Slide[];
}
export interface MindNode {
  label: string;
  children: MindNode[];
}
export interface MindMapContent {
  title: string;
  root: MindNode;
}
export interface ReportSection {
  heading: string;
  content: string;
}
export interface ReportContent {
  title: string;
  abstract: string;
  sections: ReportSection[];
  conclusion: string;
}
export interface Flashcard {
  front: string;
  back: string;
  hint: string;
}
export interface FlashcardsContent {
  title: string;
  cards: Flashcard[];
}
export interface QuizQuestion {
  question: string;
  options: string[];
  answer_index: number;
  explanation: string;
}
export interface QuizContent {
  title: string;
  questions: QuizQuestion[];
}
export interface InfographicStat {
  label: string;
  value: string;
  unit: string;
  description: string;
}
export interface InfographicSection {
  heading: string;
  icon: string;
  points: string[];
}
export interface InfographicContent {
  title: string;
  subtitle: string;
  stats: InfographicStat[];
  sections: InfographicSection[];
  takeaway: string;
}
export interface DataTableContent {
  title: string;
  caption: string;
  columns: string[];
  rows: string[][];
}

export type ArtifactContent =
  | CustomContent
  | AudioOverviewContent
  | SlideDeckContent
  | MindMapContent
  | ReportContent
  | FlashcardsContent
  | QuizContent
  | InfographicContent
  | DataTableContent;

export interface GenerateArtifactInput {
  kind: ArtifactKind;
  prompt?: string;
  title?: string;
  document_ids?: string[];
  options?: Record<string, unknown>;
  retrieve_k?: number;
}
