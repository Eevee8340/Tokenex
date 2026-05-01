import json
import os
import sqlite3
from pathlib import Path
from collections import defaultdict
from .base import BaseDetector


class CodexDetector(BaseDetector):
    name = "Codex"

    def detect(self) -> bool:
        if self.custom_path:
            return self.custom_path.exists()
        p = Path.home() / ".codex" / "state_5.sqlite"
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
            cur.execute("SELECT id, rollout_path, cwd, model FROM threads")
        except sqlite3.OperationalError:
            conn.close()
            return stats

        for thread_id, rollout_path, cwd, model in cur.fetchall():
            if not rollout_path or not os.path.exists(rollout_path):
                continue

            stats['sessions'].add(thread_id)
            project_name = "Unknown"
            if cwd:
                cwd_clean = cwd.replace('\\\\?\\', '')
                project_name = Path(cwd_clean).name or "Unknown"

            if not model:
                model = "unknown"

            with open(rollout_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if 'token_count' in line:
                        try:
                            data = json.loads(line)
                            payload = data.get('payload', {})
                            if payload.get('type') == 'token_count':
                                info = payload.get('info')
                                if not info:
                                    continue
                                last_usage = info.get('last_token_usage')
                                if not last_usage:
                                    continue

                                input_tokens = last_usage.get('input_tokens', 0)
                                cached_tokens = last_usage.get('cached_input_tokens', 0)
                                output_tokens = last_usage.get('output_tokens', 0)
                                reasoning_tokens = last_usage.get('reasoning_output_tokens', 0)
                                total_tokens = last_usage.get('total_tokens', input_tokens + output_tokens)

                                stats['total_turns'] += 1
                                stats['total_processed'] += total_tokens
                                stats['input'] += input_tokens
                                stats['output'] += output_tokens
                                stats['cached'] += cached_tokens
                                stats['thoughts'] += reasoning_tokens

                                stats['models'][model]['input'] += input_tokens
                                stats['models'][model]['output'] += output_tokens
                                stats['models'][model]['total'] += total_tokens

                                stats['projects'][project_name]['input'] += input_tokens
                                stats['projects'][project_name]['output'] += output_tokens
                                stats['projects'][project_name]['total'] += total_tokens
                        except json.JSONDecodeError:
                            pass

        conn.close()
        stats['total_sessions'] = len(stats['sessions'])
        del stats['sessions']
        stats['models'] = dict(stats['models'])
        stats['projects'] = dict(stats['projects'])
        return stats
