import json
import os
import sqlite3
from pathlib import Path
from collections import defaultdict
from .base import BaseDetector


class OpencodeDetector(BaseDetector):
    name = "Opencode"

    def detect(self) -> bool:
        if self.custom_path:
            return self.custom_path.exists()
        paths = [
            Path(os.environ.get('APPDATA', '')) / "opencode" / "opencode.db",
            Path.home() / ".local" / "share" / "opencode" / "opencode.db"
        ]
        for p in paths:
            if p.exists():
                self._found_path = p
                return True
        return False

    def scan(self, since=None, until=None) -> dict:
        db_path = getattr(self, '_found_path', self.custom_path)
        stats = {
            'total_processed': 0,
            'input': 0,
            'output': 0,
            'cached': 0,
            'thoughts': 0,
            'total_turns': 0,
            'models': defaultdict(lambda: {'input': 0, 'output': 0, 'total': 0}),
            'projects': defaultdict(lambda: {'input': 0, 'output': 0, 'total': 0}),
            'sessions': set()
        }

        if not db_path or not db_path.exists():
            return stats

        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()

        try:
            cur.execute("SELECT session_id, data FROM message")
        except sqlite3.OperationalError:
            conn.close()
            return stats

        for session_id, data_str in cur.fetchall():
            if not data_str:
                continue
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue

            if data.get('role') != 'assistant':
                continue

            tokens = data.get('tokens')
            if not tokens:
                continue

            raw_input = tokens.get('input', 0)
            output_tokens = tokens.get('output', 0)
            reasoning_tokens = tokens.get('reasoning', 0)
            cached_tokens = tokens.get('cache', {}).get('read', 0)
            input_tokens = raw_input + cached_tokens
            total_tokens = tokens.get('total', input_tokens + output_tokens + reasoning_tokens)

            if total_tokens > 0 or input_tokens > 0 or output_tokens > 0:
                stats['sessions'].add(session_id)
                stats['total_turns'] += 1
                stats['total_processed'] += total_tokens
                stats['input'] += input_tokens
                stats['output'] += output_tokens
                stats['thoughts'] += reasoning_tokens
                stats['cached'] += cached_tokens

                model = data.get('modelID', 'unknown')
                provider = data.get('providerID', '')
                if provider and provider != "unknown":
                    model = f"{provider}/{model}"

                stats['models'][model]['input'] += input_tokens
                stats['models'][model]['output'] += output_tokens
                stats['models'][model]['total'] += total_tokens

                path_data = data.get('path', {})
                project_path = path_data.get('root') or path_data.get('cwd')
                if project_path and Path(project_path).name:
                    project_name = Path(project_path).name
                else:
                    project_name = 'Unknown'

                stats['projects'][project_name]['input'] += input_tokens
                stats['projects'][project_name]['output'] += output_tokens
                stats['projects'][project_name]['total'] += total_tokens

        conn.close()
        stats['total_sessions'] = len(stats['sessions'])
        del stats['sessions']
        # Convert defaultdicts to regular dicts for serialization
        stats['models'] = dict(stats['models'])
        stats['projects'] = dict(stats['projects'])
        return stats
