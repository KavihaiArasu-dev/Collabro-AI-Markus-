/**
 * Markus AI — GitHub Adapter (§7, §13)
 * Direct port from adapters/github_adapter.py using simple-git npm package.
 */

import simpleGit, { type DefaultLogFields } from "simple-git";

class GitHubAdapter {
  constructor() {
    console.log("GitHub Adapter initialized");
  }

  async getRepoStatus(repoPath: string): Promise<Record<string, unknown>> {
    try {
      const git = simpleGit(repoPath);
      const status = await git.status();
      const branch = await git.branchLocal();

      return {
        branch: branch.current,
        is_dirty: !status.isClean(),
        untracked_files: status.not_added,
        modified_files: status.modified,
      };
    } catch (e) {
      console.error(`Error accessing git repo at ${repoPath}: ${e}`);
      return { error: String(e) };
    }
  }

  async getCommitHistory(repoPath: string, maxCount: number = 10): Promise<Record<string, unknown>[]> {
    try {
      const git = simpleGit(repoPath);
      const log = await git.log({ maxCount });

      return (log.all ?? []).map((c: DefaultLogFields) => ({
        hexsha: c.hash.slice(0, 8),
        author: c.author_name,
        message: c.message.trim(),
        date: c.date,
      }));
    } catch (e) {
      console.error(`Error getting git history at ${repoPath}: ${e}`);
      return [];
    }
  }
}

export const githubAdapter = new GitHubAdapter();
