import json
import os
import re
from pathlib import Path
from collections import defaultdict
from .base import BaseDetector


def estimate_tokens_from_text(text):
    if not text:
        return 0
    return len(text) // 4


def get_file_tokens(file_path):
    try:
        path = Path(file_path.strip('"'))
        if path.exists() and path.is_file():
            return os.path.getsize(path) // 4
    except Exception:
        pass
    return 2500


def normalize_model_name(name):
    name = name.lower()
    if 'opus' in name:
        return 'Claude Opus 4.6'
    if 'sonnet' in name:
        return 'Claude Sonnet 4.6'
    if '3.1 pro' in name or '3.1-pro' in name:
        return 'Gemini 3.1 Pro'
    if 'flash' in name:
        return 'Gemini 3 Flash'
    if 'gemini 3' in name:
        return 'Gemini 3.1 Pro'
    return 'Other/Mixed'


class AntigravityDetector(BaseDetector):
    name = "Antigravity"

    def detect(self) -> bool:
        if self.custom_path:
            return self.custom_path.exists()
        brain = Path.home() / ".gemini" / "antigravity" / "brain"
        conv = Path.home() / ".gemini" / "antigravity" / "conversations"
        if brain.exists() or conv.exists():
            self._brain_path = brain
            self._conv_path = conv
            return True
        return False

    def scan(self, since=None, until=None) -> dict:
        brain_dir = getattr(self, '_brain_path', Path.home() / ".gemini" / "antigravity" / "brain")
        conv_dir = getattr(self, '_conv_path', Path.home() / ".gemini" / "antigravity" / "conversations")

        stats = {
            'total_input': 0,
            'total_output': 0,
            'total_processed': 0,
            'input': 0,
            'output': 0,
            'cached': 0,
            'thoughts': 0,
            'total_turns': 0,
            'total_sessions': 0,
            'models': defaultdict(lambda: {'input': 0, 'output': 0, 'total': 0}),
            'projects': defaultdict(lambda: {'input': 0, 'output': 0, 'total': 0}),
            'sessions': 0
        }

        session_projects = {}

        # 1. Process Brain Logs
        log_files = []
        if brain_dir.exists():
            for root, _, files in os.walk(brain_dir):
                for file in files:
                    if file == "overview.txt":
                        log_files.append(os.path.join(root, file))

        for file_path in log_files:
            stats['sessions'] += 1
            history_tokens = 0
            current_model = "Gemini 3.1 Pro"

            session_match = re.search(r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})', str(file_path))
            session_id = session_match.group(1) if session_match else "unknown"

            project_name = "Unknown"

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            data = json.loads(line)
                            source = data.get('source')
                            content = data.get('content', '')

                            if project_name == "Unknown":
                                p_match = re.search(r'(?i)c:\\users\\[^\\]+\\([^\s"\']+)', content)
                                if p_match:
                                    parts = p_match.group(1).split('\\')
                                    project_name = parts[0]
                                    session_projects[session_id] = project_name

                            if "Model Selection` from" in content:
                                model_match = re.search(r"to (.*?)\\.", content)
                                if model_match:
                                    current_model = normalize_model_name(model_match.group(1))

                            new_tokens = estimate_tokens_from_text(content)
                            injected_this_step = 0
                            tool_calls = data.get('tool_calls', [])
                            for tool in tool_calls:
                                name = tool.get('name', '')
                                args = tool.get('args', {})
                                new_tokens += estimate_tokens_from_text(json.dumps(args))
                                if name in ['view_file', 'read_file', 'read_file_content']:
                                    path = args.get('AbsolutePath') or args.get('file_path') or args.get('TargetFile')
                                    if path:
                                        injected_this_step += get_file_tokens(path)

                            if source in ["USER_EXPLICIT", "USER"]:
                                history_tokens += (new_tokens + injected_this_step)
                            elif source == "MODEL":
                                stats['total_input'] += history_tokens
                                stats['total_output'] += new_tokens
                                stats['models'][current_model]['input'] += history_tokens
                                stats['models'][current_model]['output'] += new_tokens
                                stats['models'][current_model]['total'] += (history_tokens + new_tokens)

                                stats['projects'][project_name]['input'] += history_tokens
                                stats['projects'][project_name]['output'] += new_tokens
                                stats['projects'][project_name]['total'] += (history_tokens + new_tokens)

                                history_tokens += new_tokens
                                stats['total_turns'] += 1
                        except Exception:
                            continue
            except Exception:
                continue

            if project_name == "Unknown" and session_id not in session_projects:
                session_projects[session_id] = "Unknown"

        # 2. Process Standard Chats (.pb files)
        if conv_dir.exists():
            for pb_file in conv_dir.glob("*.pb"):
                session_id = pb_file.stem
                project_name = session_projects.get(session_id, 'Unknown')

                size = os.path.getsize(pb_file)
                final_tokens = size // 4
                estimated_processed = final_tokens * 15

                chat_input = int(estimated_processed * 0.98)
                chat_output = int(estimated_processed * 0.02)

                stats['total_input'] += chat_input
                stats['total_output'] += chat_output
                stats['models']['IDE Chat History (Mixed)']['input'] += chat_input
                stats['models']['IDE Chat History (Mixed)']['output'] += chat_output
                stats['models']['IDE Chat History (Mixed)']['total'] += (chat_input + chat_output)

                stats['projects'][project_name]['input'] += chat_input
                stats['projects'][project_name]['output'] += chat_output
                stats['projects'][project_name]['total'] += (chat_input + chat_output)

        stats['total_sessions'] = stats['sessions']
        stats['input'] = stats['total_input']
        stats['output'] = stats['total_output']
        stats['total_processed'] = stats['total_input'] + stats['total_output']
        del stats['sessions']
        stats['models'] = dict(stats['models'])
        stats['projects'] = dict(stats['projects'])
        return stats
