/**
 * Markus AI — Domain Entities & Value Objects (§1, §2)
 * Clean Architecture domain models for Conversation, Perception, RAG, and Agents.
 * Direct port from domain/entities.py.
 */

export enum MessageRole {
  SYSTEM = "system",
  USER = "user",
  ASSISTANT = "assistant",
  TOOL = "tool",
}

export interface ChatMessage {
  role: MessageRole | string;
  content: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export function createChatMessage(
  role: MessageRole | string,
  content: string,
  metadata: Record<string, unknown> = {},
): ChatMessage {
  return {
    role,
    content,
    timestamp: new Date().toISOString(),
    metadata,
  };
}

export function chatMessageToDict(msg: ChatMessage): Record<string, unknown> {
  return {
    role: msg.role,
    content: msg.content,
    timestamp: msg.timestamp,
    metadata: msg.metadata,
  };
}

export interface FaceIdentity {
  trackId: number;
  name: string;
  isOwner: boolean;
  confidence: number;
  expression: string;
  expressionConfidence: number;
  bbox: Record<string, number>;
  normalizedBbox: Record<string, number>;
}

export interface DocumentChunk {
  chunkId: string;
  docName: string;
  text: string;
  metadata: Record<string, unknown>;
  embedding?: number[];
}

export interface RAGSearchResult {
  chunk: DocumentChunk;
  similarityScore: number;
  excerpt: string;
}

export enum ProjectStatus {
  ACTIVE = "active",
  ARCHIVED = "archived",
  BUILDING = "building",
  ERROR = "error",
}

export interface Project {
  name: string;
  id: string;
  description: string;
  path: string;
  language: string;
  framework?: string;
  status: ProjectStatus;
  createdAt: string;
}

export function createProject(name: string, opts?: Partial<Project>): Project {
  return {
    name,
    id: Date.now().toString(),
    description: "",
    path: ".",
    language: "python",
    status: ProjectStatus.ACTIVE,
    createdAt: new Date().toISOString(),
    ...opts,
  };
}
