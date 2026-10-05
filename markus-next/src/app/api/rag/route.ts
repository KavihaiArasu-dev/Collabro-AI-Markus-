/**
 * Markus AI — RAG API Routes
 */

import { NextRequest, NextResponse } from "next/server";
import { documentLoader } from "@/lib/rag/document-loader";
import { ragRetriever } from "@/lib/rag/retriever";
import { vectorStore } from "@/lib/rag/vector-store";

export async function GET() {
  return NextResponse.json({
    documents: vectorStore.getDocumentNames(),
    total_chunks: vectorStore.chunks.size,
    stats: ragRetriever.getStats(),
  });
}

export async function POST(request: NextRequest) {
  const body = await request.json();
  const action = body.action || "query";

  if (action === "query") {
    const query = body.query || "";
    const topK = body.top_k || 4;
    const [contextStr, results] = ragRetriever.buildRagContext(query, topK);

    return NextResponse.json({
      query,
      results_count: results.length,
      results: results.map((r) => ({
        chunk_id: r.chunk.chunkId,
        doc_name: r.chunk.docName,
        similarity_score: r.similarityScore,
        text: r.chunk.text,
      })),
      context_prompt: contextStr,
    });
  }

  if (action === "ingest-text") {
    const title = body.title || "untitled";
    const content = body.content || "";
    const chunks = documentLoader.ingestText(content, title);
    return NextResponse.json({
      status: "success",
      doc_name: title,
      chunks_created: chunks.length,
      total_indexed_chunks: vectorStore.chunks.size,
    });
  }

  if (action === "ingest-directory") {
    const dirPath = body.path || "./data/documents";
    const count = documentLoader.ingestDirectory(dirPath);
    return NextResponse.json({ status: "ingested", chunks: count });
  }

  if (action === "clear") {
    vectorStore.clear();
    return NextResponse.json({ status: "success", message: "Cleared all RAG knowledge" });
  }

  return NextResponse.json({ error: `Unknown action: ${action}` }, { status: 400 });
}
