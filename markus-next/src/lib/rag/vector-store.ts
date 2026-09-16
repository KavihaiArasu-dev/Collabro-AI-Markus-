/**
 * Markus AI — Lightweight Embedded Vector Store
 * TF-IDF sparse embeddings with cosine similarity.
 * Direct port from rag/vector_store.py.
 */

import * as fs from "fs";
import * as path from "path";
import type { DocumentChunk, RAGSearchResult } from "@/lib/domain/entities";

const STORE_PATH = path.join("data", "vector_store.json");

class VectorStore {
  chunks: Map<string, DocumentChunk> = new Map();
  private idf: Map<string, number> = new Map();
  private storagePath: string;

  constructor(storagePath: string = STORE_PATH) {
    this.storagePath = storagePath;
    this._loadStore();
  }

  private _tokenize(text: string): string[] {
    const matches = text.match(/\b[a-zA-Z0-9_-]{2,}\b/g);
    return (matches ?? []).map((w) => w.toLowerCase());
  }

  private _computeTfVector(tokens: string[]): Map<string, number> {
    const counts = new Map<string, number>();
    for (const t of tokens) {
      counts.set(t, (counts.get(t) ?? 0) + 1);
    }
    const total = tokens.length || 1;
    const tf = new Map<string, number>();
    for (const [term, count] of counts) {
      tf.set(term, count / total);
    }
    return tf;
  }

  private _recalculateIdf(): void {
    const docCount = this.chunks.size;
    if (docCount === 0) {
      this.idf.clear();
      return;
    }

    const docFreq = new Map<string, number>();
    for (const chunk of this.chunks.values()) {
      const uniqueTokens = new Set(this._tokenize(chunk.text));
      for (const token of uniqueTokens) {
        docFreq.set(token, (docFreq.get(token) ?? 0) + 1);
      }
    }

    this.idf.clear();
    for (const [term, freq] of docFreq) {
      this.idf.set(term, Math.log((1.0 + docCount) / (1.0 + freq)) + 1.0);
    }
  }

  private _embedText(text: string): Map<string, number> {
    const tokens = this._tokenize(text);
    const tf = this._computeTfVector(tokens);
    const vector = new Map<string, number>();
    let normSq = 0.0;

    for (const [term, tfVal] of tf) {
      const idfVal = this.idf.get(term) ?? 1.0;
      const val = tfVal * idfVal;
      vector.set(term, val);
      normSq += val * val;
    }

    const norm = Math.sqrt(normSq) || 1.0;
    const normalized = new Map<string, number>();
    for (const [t, v] of vector) {
      normalized.set(t, v / norm);
    }
    return normalized;
  }

  addChunks(chunks: DocumentChunk[]): void {
    for (const chunk of chunks) {
      this.chunks.set(chunk.chunkId, chunk);
    }
    this._recalculateIdf();
    this._saveStore();
    console.log(`VectorStore: Indexed ${chunks.length} chunks (Total: ${this.chunks.size})`);
  }

  similaritySearch(query: string, topK: number = 4): RAGSearchResult[] {
    if (this.chunks.size === 0 || !query.trim()) return [];

    const queryVec = this._embedText(query);
    const scores: Array<[string, number]> = [];

    for (const [chunkId, chunk] of this.chunks) {
      const chunkVec = this._embedText(chunk.text);
      let dotProduct = 0;
      for (const [term, qVal] of queryVec) {
        const cVal = chunkVec.get(term);
        if (cVal !== undefined) {
          dotProduct += qVal * cVal;
        }
      }

      // Exact keyword boost
      const queryLower = query.toLowerCase();
      const words = queryLower.split(/\s+/).filter((w) => w.length > 3);
      const chunkLower = chunk.text.toLowerCase();
      if (words.some((w) => chunkLower.includes(w))) {
        dotProduct += 0.15;
      }

      if (dotProduct > 0.05) {
        scores.push([chunkId, dotProduct]);
      }
    }

    scores.sort((a, b) => b[1] - a[1]);
    const topResults = scores.slice(0, topK);

    return topResults.map(([chunkId, score]) => {
      const chunk = this.chunks.get(chunkId)!;
      const excerpt = chunk.text.slice(0, 280) + (chunk.text.length > 280 ? "..." : "");
      return { chunk, similarityScore: Math.round(score * 1000) / 1000, excerpt };
    });
  }

  clear(): void {
    this.chunks.clear();
    this.idf.clear();
    this._saveStore();
  }

  getDocumentNames(): string[] {
    const names = new Set<string>();
    for (const c of this.chunks.values()) {
      names.add(c.docName);
    }
    return Array.from(names);
  }

  private _saveStore(): void {
    try {
      const dir = path.dirname(this.storagePath);
      fs.mkdirSync(dir, { recursive: true });
      const data: Record<string, unknown> = {};
      for (const [chunkId, c] of this.chunks) {
        data[chunkId] = {
          chunk_id: c.chunkId,
          doc_name: c.docName,
          text: c.text,
          metadata: c.metadata,
        };
      }
      fs.writeFileSync(this.storagePath, JSON.stringify(data, null, 2), "utf-8");
    } catch (e) {
      console.warn(`Failed to save VectorStore: ${e}`);
    }
  }

  private _loadStore(): void {
    try {
      if (fs.existsSync(this.storagePath)) {
        const raw = fs.readFileSync(this.storagePath, "utf-8");
        const data = JSON.parse(raw) as Record<string, Record<string, unknown>>;
        for (const [cid, item] of Object.entries(data)) {
          this.chunks.set(cid, {
            chunkId: item.chunk_id as string,
            docName: item.doc_name as string,
            text: item.text as string,
            metadata: (item.metadata as Record<string, unknown>) ?? {},
          });
        }
        this._recalculateIdf();
      }
    } catch (e) {
      console.warn(`Failed to load VectorStore: ${e}`);
      this.chunks.clear();
    }
  }
}

// Singleton
export const vectorStore = new VectorStore();
