/**
 * Markus AI — RAG Document Chunker
 * Splits text into overlapping semantic windows.
 * Direct port from rag/chunker.py.
 */

import type { DocumentChunk } from "@/lib/domain/entities";

export class DocumentChunker {
  private chunkSize: number;
  private chunkOverlap: number;

  constructor(chunkSize: number = 450, chunkOverlap: number = 80) {
    this.chunkSize = chunkSize;
    this.chunkOverlap = chunkOverlap;
  }

  chunkText(text: string, docName: string): DocumentChunk[] {
    if (!text || !text.trim()) return [];

    const normalized = text.replace(/\r\n/g, "\n");
    const paragraphs = normalized.split(/\n\s*\n/);

    const chunks: DocumentChunk[] = [];
    let currentText = "";
    let chunkIdx = 1;

    for (const p of paragraphs) {
      const pClean = p.trim();
      if (!pClean) continue;

      if (currentText.length + pClean.length <= this.chunkSize) {
        currentText = (currentText ? currentText + "\n\n" + pClean : pClean).trim();
      } else {
        if (currentText) {
          chunks.push({
            chunkId: `${docName}_chunk_${chunkIdx}`,
            docName,
            text: currentText,
            metadata: { doc_name: docName, chunk_index: chunkIdx },
          });
          chunkIdx++;
          const overlapStart = Math.max(0, currentText.length - this.chunkOverlap);
          const overlapPart = currentText.slice(overlapStart);
          currentText = (overlapPart + "\n\n" + pClean).trim();
        } else {
          // Single paragraph exceeds chunkSize — split by sentences
          const sentences = pClean.split(/(?<=[.!?])\s+/);
          let subText = "";
          for (const s of sentences) {
            if (subText.length + s.length <= this.chunkSize) {
              subText = (subText ? subText + " " + s : s).trim();
            } else {
              if (subText) {
                chunks.push({
                  chunkId: `${docName}_chunk_${chunkIdx}`,
                  docName,
                  text: subText,
                  metadata: { doc_name: docName, chunk_index: chunkIdx },
                });
                chunkIdx++;
              }
              subText = s;
            }
          }
          if (subText) {
            currentText = subText;
          }
        }
      }
    }

    if (currentText) {
      chunks.push({
        chunkId: `${docName}_chunk_${chunkIdx}`,
        docName,
        text: currentText,
        metadata: { doc_name: docName, chunk_index: chunkIdx },
      });
    }

    return chunks;
  }
}
