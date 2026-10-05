/**
 * Markus AI — Memory Manager (§6b)
 *
 * Layered memory system with short-term (in-memory) and persistent (SQLite) storage.
 */

import { MemoryCategory, MemoryType } from "@/lib/config/constants";
import { v4 as uuidv4 } from "uuid";

interface MemoryEntry {
  id: string;
  content: string;
  category: MemoryCategory;
  memoryType: MemoryType;
  tags: string[];
  importance: number;
  createdAt: string;
  lastAccessedAt: string;
  accessCount: number;
}

// Map category to memory type once
const CATEGORY_TO_TYPE: Record<MemoryCategory, MemoryType> = {
  [MemoryCategory.TEMPORARY]: MemoryType.SHORT_TERM,
  [MemoryCategory.SESSION]: MemoryType.EPISODIC,
  [MemoryCategory.PREFERENCE]: MemoryType.PREFERENCE,
  [MemoryCategory.PROJECT]: MemoryType.PROJECT,
  [MemoryCategory.IMPORTANT]: MemoryType.EPISODIC,
};

class MemoryManager {
  private _shortTerm: MemoryEntry[] = [];
  private _maxShortTerm: number = 100;
  private _dbPath: string;
  private _dbInitialized: boolean = false;
  private _dbFailed: boolean = false;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private _db: any = null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private _insertStmt: any = null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  private _searchStmt: any = null;

  constructor(dbPath: string = "./data/memory.db") {
    this._dbPath = dbPath;
    console.log("Memory Manager initialized");
  }

  /**
   * Initialize and get SQLite database with better-sqlite3 (lazy persistent handle).
   */
  private _getDb(): unknown {
    if (this._db) return this._db;
    if (this._dbFailed) return null;
    try {
      // Ensure directory exists
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const path = require("path");
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const fs = require("fs");
      const dir = path.dirname(this._dbPath);
      if (!fs.existsSync(dir)) {
        fs.mkdirSync(dir, { recursive: true });
      }

      // Use dynamic import to avoid issues in edge runtime
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      const Database = require("better-sqlite3");
      this._db = new Database(this._dbPath);
      try {
        this._db.pragma("journal_mode = WAL");
        this._db.pragma("synchronous = NORMAL");
      } catch {
        // Pragma may fail in memory or locked modes, ignore
      }

      this._db.exec(`
        CREATE TABLE IF NOT EXISTS memories (
          id TEXT PRIMARY KEY,
          content TEXT NOT NULL,
          category TEXT NOT NULL,
          memory_type TEXT NOT NULL,
          tags TEXT DEFAULT '[]',
          importance REAL DEFAULT 0.5,
          created_at TEXT NOT NULL,
          last_accessed_at TEXT NOT NULL,
          access_count INTEGER DEFAULT 0
        )
      `);

      this._insertStmt = this._db.prepare(
        `INSERT OR REPLACE INTO memories (id, content, category, memory_type, tags, importance, created_at, last_accessed_at, access_count)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
      );
      this._searchStmt = this._db.prepare(
        `SELECT * FROM memories WHERE content LIKE ? ORDER BY importance DESC LIMIT ?`,
      );

      this._dbInitialized = true;
      return this._db;
    } catch (e) {
      console.warn(`Memory DB init failed (expected in edge runtime): ${e}`);
      this._db = null;
      this._dbFailed = true;
      return null;
    }
  }

  /**
   * Initialize SQLite database (lazy).
   */
  private _initDb(): void {
    this._getDb();
  }

  /**
   * Store a memory.
   */
  store(
    content: string,
    category: MemoryCategory = MemoryCategory.SESSION,
    tags: string[] = [],
    importance: number = 0.5,
  ): string {
    const entry: MemoryEntry = {
      id: uuidv4().slice(0, 8),
      content,
      category,
      memoryType: this._categoryToType(category),
      tags,
      importance,
      createdAt: new Date().toISOString(),
      lastAccessedAt: new Date().toISOString(),
      accessCount: 0,
    };

    // Short-term (always)
    this._shortTerm.push(entry);
    if (this._shortTerm.length > this._maxShortTerm) {
      this._shortTerm.shift();
    }

    // Persistent (if not temporary)
    if (category !== MemoryCategory.TEMPORARY) {
      this._persistMemory(entry);
    }

    console.log(`Memory stored: ${entry.id} (${category})`);
    return entry.id;
  }

  /**
   * Recall memories matching a query.
   */
  recall(query: string, limit: number = 5): MemoryEntry[] {
    const queryLower = query.toLowerCase();

    // Search short-term first
    const results = this._shortTerm
      .filter((m) => {
        return (
          m.content.toLowerCase().includes(queryLower) ||
          m.tags.some((t) => queryLower.includes(t.toLowerCase()))
        );
      })
      .sort((a, b) => b.importance - a.importance)
      .slice(0, limit);

    // If not enough, search persistent
    if (results.length < limit) {
      const persistent = this._searchPersistent(query, limit - results.length);
      results.push(...persistent);
    }

    return results;
  }

  /**
   * Get memory stats.
   */
  getStats(): Record<string, unknown> {
    return {
      short_term_count: this._shortTerm.length,
      short_term_max: this._maxShortTerm,
      db_path: this._dbPath,
      db_initialized: this._dbInitialized,
    };
  }

  /**
   * Clear all short-term memory.
   */
  clearShortTerm(): void {
    this._shortTerm = [];
  }

  private _categoryToType(category: MemoryCategory): MemoryType {
    return CATEGORY_TO_TYPE[category] ?? MemoryType.SHORT_TERM;
  }

  private _persistMemory(entry: MemoryEntry): void {
    try {
      this._getDb();
      if (!this._insertStmt) return;
      this._insertStmt.run(
        entry.id,
        entry.content,
        entry.category,
        entry.memoryType,
        JSON.stringify(entry.tags),
        entry.importance,
        entry.createdAt,
        entry.lastAccessedAt,
        entry.accessCount,
      );
    } catch (e) {
      console.warn(`Failed to persist memory: ${e}`);
    }
  }

  private _searchPersistent(query: string, limit: number): MemoryEntry[] {
    try {
      this._getDb();
      if (!this._searchStmt) return [];
      const rows = this._searchStmt.all(`%${query}%`, limit);

      return (rows as Record<string, unknown>[]).map((row) => ({
        id: row.id as string,
        content: row.content as string,
        category: row.category as MemoryCategory,
        memoryType: row.memory_type as MemoryType,
        tags: JSON.parse((row.tags as string) || "[]"),
        importance: row.importance as number,
        createdAt: row.created_at as string,
        lastAccessedAt: row.last_accessed_at as string,
        accessCount: row.access_count as number,
      }));
    } catch {
      return [];
    }
  }

  close(): void {
    if (this._db) {
      try {
        this._db.close();
      } catch {
        // Ignore close errors
      }
      this._db = null;
      this._insertStmt = null;
      this._searchStmt = null;
      this._dbInitialized = false;
      this._dbFailed = false;
    }
  }
}

// Singleton
export const memoryManager = new MemoryManager();
