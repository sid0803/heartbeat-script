import subprocess
import os
from typing import List, Dict, Any
from .base import BaseConnector

class GitConnector(BaseConnector):
    def __init__(self, repo_path: str, max_commits: int = 5):
        super().__init__()
        self.repo_path = repo_path
        self.max_commits = max_commits

    @property
    def name(self) -> str:
        return "git_project"

    def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch recent commit messages from the local repository."""
        if not os.path.exists(self.repo_path):
            return [{"source": self.name, "content": f"Repo path {self.repo_path} not found", "priority": "low"}]

        try:
            # Command to get last N commit messages
            cmd = f"git -C {self.repo_path} log -n {self.max_commits} --pretty=format:'%s (%an)'"
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode != 0:
                return [{"source": self.name, "content": "Not a git repository or git not installed", "priority": "low"}]

            commits = result.stdout.strip().split('\n')
            if not commits or not commits[0]:
                return [{"source": self.name, "content": "No recent changes found in project.", "priority": "low"}]

            return [
                {
                    "source": self.name,
                    "type": "commit_history",
                    "content": f"Recent updates: {'; '.join(commits)}",
                    "priority": "medium",
                    "timestamp": os.path.getmtime(self.repo_path)
                }
            ]
        except Exception as e:
            self.handle_error(e)
            return []
