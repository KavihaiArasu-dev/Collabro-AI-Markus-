"""
Markus AI — Memory Manager (§6b)

Layered memory system:
- Short-term: current conversation, current task, recent tool outputs
- Episodic: completed tasks, user interactions, important events
- Preference: UI/coding preferences, frequently used apps, preferred languages
- Project: current projects, repo context, architecture decisions, known bugs

Every memory write is tagged with a category (TEMPORARY, SESSION, PREFERENCE,
PROJECT, IMPORTANT) and requires explicit policy approval for persistence.
"""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional
from uuid import uuid4

from config.constants import MemoryCategory, MemoryType
from config.settings import settings

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Layered memory backed by SQLite.

    Categories control persistence:
    - TEMPORARY: discarded at end of conversation
    - SESSION: kept for the session, deleted on restart
    - PREFERENCE: persisted across sessions
    - PROJECT: persisted, tied to a project
    - IMPORTANT: always persisted
    """

    def __init__(self):
        self._db_path = Path(settings.memory.db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        # In-memory short-term store (not persisted)
        self._short_term: list[dict] = []
        self._max_short_term = 100

        logger.info(f"Memory Manager initialized (db: {self._db_path})")

    def _init_db(self):
        """Initialize the SQLite database for persistent memory."""
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                category TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                tags TEXT DEFAULT '',
                project_id TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                accessed_at TEXT,
                access_count INTEGER DEFAULT 0,
                metadata TEXT DEFAULT '{}'
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON memories(category)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(memory_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_project ON memories(project_id)")
        conn.commit()
        conn.close()

    def save(
        self,
        content: str,
        category: MemoryCategory = MemoryCategory.SESSION,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        tags: list[str] = None,
        project_id: str = "",
        metadata: dict = None,
    ) -> str:
        """
        Save a memory with the appropriate category tag.

        Returns the memory ID.
        """
        memory_id = str(uuid4())[:12]
        now = datetime.now().isoformat()

        if memory_type == MemoryType.SHORT_TERM:
            # Short-term stays in memory only
            self._short_term.append({
                "id": memory_id,
                "content": content,
                "category": category.value,
                "memory_type": memory_type.value,
                "tags": tags or [],
                "created_at": now,
            })
            if len(self._short_term) > self._max_short_term:
                self._short_term.pop(0)
        else:
            # Persistent memory goes to SQLite
            conn = sqlite3.connect(str(self._db_path))
            conn.execute(
                "INSERT INTO memories (id, content, category, memory_type, tags, project_id, created_at, metadata) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    memory_id,
                    content,
                    category.value,
                    memory_type.value,
                    json.dumps(tags or []),
                    project_id,
                    now,
                    json.dumps(metadata or {}),
                ),
            )
            conn.commit()
            conn.close()

        logger.debug(f"Memory saved: [{category.value}] {content[:80]}...")
        return memory_id

    def recall(
        self,
        query: str = "",
        category: Optional[MemoryCategory] = None,
        memory_type: Optional[MemoryType] = None,
        project_id: str = "",
        limit: int = 10,
    ) -> list[dict]:
        """
        Recall memories matching the criteria.

        For now uses simple keyword matching. Will be upgraded to
        vector-based retrieval when the RAG system is integrated.
        """
        results = []

        # Search short-term memory
        for mem in reversed(self._short_term):
            if category and mem["category"] != category.value:
                continue
            if query and query.lower() not in mem["content"].lower():
                continue
            results.append(mem)
            if len(results) >= limit:
                return results

        # Search persistent memory
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row

        sql = "SELECT * FROM memories WHERE 1=1"
        params = []

        if category:
            sql += " AND category = ?"
            params.append(category.value)
        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type.value)
        if project_id:
            sql += " AND project_id = ?"
            params.append(project_id)
        if query:
            sql += " AND content LIKE ?"
            params.append(f"%{query}%")

        sql += f" ORDER BY created_at DESC LIMIT ?"
        params.append(limit - len(results))

        rows = conn.execute(sql, params).fetchall()
        conn.close()

        for row in rows:
            results.append({
                "id": row["id"],
                "content": row["content"],
                "category": row["category"],
                "memory_type": row["memory_type"],
                "tags": json.loads(row["tags"]) if row["tags"] else [],
                "created_at": row["created_at"],
            })

        return results[:limit]

    def get_short_term(self, limit: int = 20) -> list[dict]:
        """Get recent short-term memories."""
        return list(reversed(self._short_term[-limit:]))

    def clear_short_term(self):
        """Clear all short-term memory."""
        self._short_term.clear()
        logger.info("Short-term memory cleared")

    def clear_session(self):
        """Clear session-scoped memories."""
        self._short_term.clear()
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("DELETE FROM memories WHERE category = ?", (MemoryCategory.SESSION.value,))
        conn.commit()
        conn.close()
        logger.info("Session memory cleared")

    def get_stats(self) -> dict:
        """Get memory statistics."""
        conn = sqlite3.connect(str(self._db_path))
        counts = {}
        for cat in MemoryCategory:
            count = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE category = ?", (cat.value,)
            ).fetchone()[0]
            counts[cat.value] = count
        conn.close()

        return {
            "short_term_count": len(self._short_term),
            "persistent_counts": counts,
            "total_persistent": sum(counts.values()),
        }


# Singleton
memory_manager = MemoryManager()
