import os
from typing import List, Dict, Any
from .base import BaseConnector

class FileProjectConnector(BaseConnector):
    def __init__(self, project_path: str):
        super().__init__()
        self.project_path = project_path
        self._ignore_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'env', 'dist', 'build'}

    @property
    def name(self) -> str:
        return "full_project_analysis"

    def _get_structure(self, path: str, depth: int = 2) -> str:
        """Get a simplified view of the project structure."""
        structure = []
        try:
            for root, dirs, files in os.walk(path):
                # Filter ignore dirs
                dirs[:] = [d for d in dirs if d not in self._ignore_dirs]
                
                rel_path = os.path.relpath(root, path)
                if rel_path == ".":
                    rel_path = ""
                
                level = rel_path.count(os.sep)
                if level >= depth:
                    continue
                
                indent = "  " * level
                folder_name = os.path.basename(root) or os.path.basename(path)
                structure.append(f"{indent}📂 {folder_name}/")
                
                for f in files[:10]: # Limit files per dir
                    structure.append(f"{indent}  📄 {f}")
        except Exception:
            pass
        return "\n".join(structure)

    def fetch_data(self) -> List[Dict[str, Any]]:
        """Scan project files to provide a high-level overview."""
        if not os.path.exists(self.project_path):
            return []

        # 1. Get structure
        structure = self._get_structure(self.project_path)

        # 2. Try to find a README or main info file
        info_content = ""
        for f in ['README.md', 'README.txt', 'package.json', 'requirements.txt']:
            full_f = os.path.join(self.project_path, f)
            if os.path.exists(full_f):
                try:
                    with open(full_f, 'r', encoding='utf-8') as file:
                        # Grab first 500 chars for context
                        info_content += f"\n--- {f} ---\n{file.read(500)}..."
                except Exception:
                    pass

        return [
            {
                "source": self.name,
                "type": "codebase_overview",
                "content": f"Project structure:\n{structure}\nKey Info:\n{info_content}",
                "priority": "medium",
                "timestamp": os.path.getmtime(self.project_path)
            }
        ]
