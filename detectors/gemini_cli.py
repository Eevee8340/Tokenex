import json
import os
import glob
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from .base import BaseDetector


class GeminiCLIDetector(BaseDetector):
    name = "Gemini CLI"

    def detect(self) -> bool:
        if self.custom_path:
            return self.custom_path.exists()
        p = Path.home() / ".gemini" / "tmp"
        if p.exists():
            self._found_path = p
            return True
        return False

    def scan(self, since=None, until=None) -> dict:
        tmp_dir = getattr(self, '_found_path', self.custom_path)
        stats = {
            'total_processed': 0,
            'input': 0,
            'output': 0,
            'cached': 0,
            'thoughts': 0,
            'total_turns': 0,
            'total_sessions': 0,
            'models': defaultdict(lambda: {'input': 0, 'output': 0, 'total': 0}),
            'projects': defaultdict(lambda: {'total': 0, 'input': 0, 'output': 0}),
            'timeline': [],
        }

        if not tmp_dir or not tmp_dir.exists():
            return stats

        search_pattern = os.path.join(str(tmp_dir), '*', 'chats', '**', '*.json*')
        chat_files = glob.glob(search_pattern, recursive=True)

        for file_path in chat_files:
            path_parts = Path(file_path).parts
            try:
                chats_index = path_parts.index('chats')
                project_alias = path_parts[chats_index - 1]
            except ValueError:
                project_alias = 'unknown'

            file_has_turns = False
            is_jsonl = file_path.endswith('.jsonl')

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    if is_jsonl:
                        for line in f:
                            try:
                                data = json.loads(line)
                                msg_time_str = data.get('timestamp') or data.get('lastUpdated')
                                msg_time = self._parse_iso(msg_time_str) if msg_time_str else None

                                if msg_time:
                                    if since and msg_time < since:
                                        continue
                                    if until and msg_time > until:
                                        continue

                                tokens = data.get('tokens')
                                if tokens:
                                    msg_total = tokens.get('total', 0)
                                    stats['input'] += tokens.get('input', 0)
                                    stats['output'] += tokens.get('output', 0)
                                    stats['cached'] += tokens.get('cached', 0)
                                    stats['thoughts'] += tokens.get('thoughts', 0)
                                    stats['total_processed'] += msg_total
                                    stats['total_turns'] += 1
                                    model = data.get('model', 'unknown')
                                    stats['models'][model]['input'] = stats['models'][model].get('input', 0) + tokens.get('input', 0)
                                    stats['models'][model]['output'] = stats['models'][model].get('output', 0) + tokens.get('output', 0)
                                    stats['models'][model]['total'] = stats['models'][model].get('total', 0) + msg_total
                                    stats['projects'][project_alias]['total'] += msg_total
                                    stats['projects'][project_alias]['input'] += tokens.get('input', 0)
                                    stats['projects'][project_alias]['output'] += tokens.get('output', 0)
                                    if msg_time:
                                        stats['timeline'].append({'date': msg_time, 'tokens': msg_total})
                                    file_has_turns = True
                            except json.JSONDecodeError:
                                continue
                    else:
                        data = json.load(f)
                        messages = data if isinstance(data, list) else data.get('messages', [])
                        for msg in messages:
                            if not isinstance(msg, dict):
                                continue
                            msg_time_str = msg.get('timestamp')
                            msg_time = self._parse_iso(msg_time_str) if msg_time_str else None

                            if msg_time:
                                if since and msg_time < since:
                                    continue
                                if until and msg_time > until:
                                    continue

                            tokens = msg.get('tokens')
                            if tokens:
                                msg_total = tokens.get('total', 0)
                                stats['input'] += tokens.get('input', 0)
                                stats['output'] += tokens.get('output', 0)
                                stats['cached'] += tokens.get('cached', 0)
                                stats['thoughts'] += tokens.get('thoughts', 0)
                                stats['total_processed'] += msg_total
                                stats['total_turns'] += 1
                                model = msg.get('model', 'unknown')
                                stats['models'][model]['input'] = stats['models'][model].get('input', 0) + tokens.get('input', 0)
                                stats['models'][model]['output'] = stats['models'][model].get('output', 0) + tokens.get('output', 0)
                                stats['models'][model]['total'] = stats['models'][model].get('total', 0) + msg_total
                                stats['projects'][project_alias]['total'] += msg_total
                                stats['projects'][project_alias]['input'] += tokens.get('input', 0)
                                stats['projects'][project_alias]['output'] += tokens.get('output', 0)
                                if msg_time:
                                    stats['timeline'].append({'date': msg_time, 'tokens': msg_total})
                                file_has_turns = True
            except Exception:
                continue

            if file_has_turns:
                stats['total_sessions'] += 1

        stats['models'] = dict(stats['models'])
        stats['projects'] = dict(stats['projects'])
        return stats

    @staticmethod
    def _parse_iso(dt_str: str) -> datetime:
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1] + '+00:00'
        try:
            return datetime.fromisoformat(dt_str).replace(tzinfo=None)
        except ValueError:
            return datetime.min
