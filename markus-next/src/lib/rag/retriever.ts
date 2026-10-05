/**
 * Markus AI — RAG Retriever & Knowledge Augmenter (§6b)
 */

import { vectorStore } from "./vector-store";
import type { RAGSearchResult } from "@/lib/domain/entities";

class RAGRetriever {
  private defaultTopK: number;
  private similarityThreshold: number;

  constructor(defaultTopK: number = 3, similarityThreshold: number = 0.12) {
    this.defaultTopK = defaultTopK;
    this.similarityThreshold = similarityThreshold;
  }

  retrieve(query: string, topK: number = 3): RAGSearchResult[] {
    const results = vectorStore.similaritySearch(query, topK);
    return results.filter((r) => r.similarityScore >= this.similarityThreshold);
  }

  buildRagContext(query: string, topK: number = 3): [string, RAGSearchResult[]] {
    const matches = this.retrieve(query, topK);
    if (matches.length === 0) {
      return ["", []];
    }

    const lines: string[] = [
      "--- KNOWLEDGE BASE CONTEXT (From User's Documents) ---",
      "Use the following excerpts to answer the user's question accurately when relevant:",
    ];

    matches.forEach((match, idx) => {
      lines.push(`\n[Source #${idx + 1}: ${match.chunk.docName} (Relevance ${Math.round(match.similarityScore * 100)}%)]`);
      lines.push(match.chunk.text.trim());
    });

    lines.push("--- END KNOWLEDGE BASE CONTEXT ---");
    return [lines.join("\n"), matches];
  }

  getStats(): Record<string, unknown> {
    return {
      total_chunks: vectorStore.chunks.size,
      documents: vectorStore.getDocumentNames(),
      document_count: vectorStore.getDocumentNames().length,
    };
  }

  query(queryText: string, topK: number = 5): Record<string, unknown>[] {
    const results = this.retrieve(queryText, topK);
    return results.map((r) => ({
      chunk_id: r.chunk.chunkId,
      doc_name: r.chunk.docName,
      similarity_score: r.similarityScore,
      excerpt: r.excerpt,
    }));
  }
}

// Singleton
export const ragRetriever = new RAGRetriever();
