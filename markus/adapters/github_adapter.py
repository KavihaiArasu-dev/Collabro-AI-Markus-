"""
Markus AI — GitHub Adapter (§7, §13)
External service adapter for interacting with GitHub repositories.
"""

from __future__ import annotations

import logging
from typing import Any, Optional
import git

logger = logging.getLogger(__name__)


class GitHubAdapter:
    """Adapter for Git and GitHub workflows."""

    def __init__(self, token: Optional[str] = None):
        self.token = token
        logger.info("GitHub Adapter initialized")

    def get_repo_status(self, repo_path: str) -> dict[str, Any]:
        """Get repository branch, modified files, and untracked status."""
        try:
            repo = git.Repo(repo_path)
            return {
                "branch": repo.active_branch.name,
                "is_dirty": repo.is_dirty(),
                "untracked_files": repo.untracked_files,
                "modified_files": [item.a_path for item in repo.index.diff(None)],
            }
        except Exception as e:
            logger.error(f"Error accessing git repo at {repo_path}: {e}")
            return {"error": str(e)}

    def get_commit_history(self, repo_path: str, max_count: int = 10) -> list[dict[str, Any]]:
        """Get recent commits."""
        try:
            repo = git.Repo(repo_path)
            commits = list(repo.iter_commits(max_count=max_count))
            return [
                {
                    "hexsha": c.hexsha[:8],
                    "author": c.author.name,
                    "message": c.message.strip(),
                    "date": c.committed_datetime.isoformat(),
                }
                for c in commits
            ]
        except Exception as e:
            logger.error(f"Error getting git history at {repo_path}: {e}")
            return []


# Singleton
github_adapter = GitHubAdapter()
