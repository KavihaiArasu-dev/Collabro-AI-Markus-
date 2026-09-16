/**
 * Markus AI — Document Ingestion & Loader
 * Direct port from rag/document_loader.py.
 */

import * as fs from "fs";
import * as path from "path";
import type { DocumentChunk } from "@/lib/domain/entities";
import { DocumentChunker } from "./chunker";
import { vectorStore } from "./vector-store";

class DocumentLoader {
  private chunker: DocumentChunker;

  constructor() {
    this.chunker = new DocumentChunker();
  }

  ingestText(text: string, docName: string): DocumentChunk[] {
    const chunks = this.chunker.chunkText(text, docName);
    if (chunks.length > 0) {
      vectorStore.addChunks(chunks);
    }
    return chunks;
  }

  ingestFile(filePath: string): DocumentChunk[] {
    if (!fs.existsSync(filePath)) {
      console.warn(`File not found: ${filePath}`);
      return [];
    }

    const docName = path.basename(filePath);
    const ext = path.extname(filePath).toLowerCase();

    try {
      const textExts = [".md", ".txt", ".py", ".js", ".ts", ".json", ".html", ".css", ".yaml", ".yml"];
      if (textExts.includes(ext) || !ext) {
        const content = fs.readFileSync(filePath, "utf-8");
        return this.ingestText(content, docName);
      }
      // For other file types, try reading as text
      const content = fs.readFileSync(filePath, "utf-8");
      return this.ingestText(content, docName);
    } catch (e) {
      console.error(`Failed to ingest file ${filePath}: ${e}`);
      return [];
    }
  }

  ingestDirectory(dirPath: string = "./data/documents"): number {
    if (!fs.existsSync(dirPath)) {
      fs.mkdirSync(dirPath, { recursive: true });
      return 0;
    }

    let totalChunks = 0;
    const walk = (dir: string) => {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          walk(fullPath);
        } else {
          const chunks = this.ingestFile(fullPath);
          totalChunks += chunks.length;
        }
      }
    };

    walk(dirPath);
    console.log(`Ingested directory '${dirPath}': ${totalChunks} total chunks created.`);
    return totalChunks;
  }
}

// Singleton
export const documentLoader = new DocumentLoader();
