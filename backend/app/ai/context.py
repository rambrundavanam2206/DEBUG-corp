import hashlib
import json
import re
from dataclasses import dataclass, field

from .schemas import AnalysisFailure, Diagnosis

MAX_CALLS = 12
MAX_TOOLS = 18
MAX_SOURCE_BYTES = 48000
MAX_CONTEXT_BYTES = 100000
SECRET_PATTERNS = [
    r"\b(?:gsk_|sb_secret_|sk-proj-)[A-Za-z0-9_-]{16,}",
    r"\bAIza[A-Za-z0-9_-]{20,}",
    r"(?i)(?:api[_-]?key|secret|password|access[_-]?token)\s*[:=]\s*[\"\'][^\"\'\n]{8,}[\"\']",
    r"-----BEGIN [^-]*PRIVATE KEY-----[\s\S]*?-----END [^-]*PRIVATE KEY-----",
]


def redact(text: str) -> str:
    # Preserve newlines so evidence refers to the original source's line numbers.
    for pattern in SECRET_PATTERNS:
        text = re.sub(
            pattern, lambda m: "\n".join("[REDACTED]" for _ in m.group().split("\n")), text
        )
    return text


def snapshot_hash(files: dict, problem: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            {"files": files, "problem": problem}, sort_keys=True, ensure_ascii=False
        ).encode()
    ).hexdigest()


@dataclass
class Investigation:
    files: dict[str, str]
    calls: int = 0
    tools: int = 0
    source_bytes: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    spans: dict[str, set[int]] = field(default_factory=dict)
    specialists: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    provider_used: str = ""
    model_used: str = ""
    fallback_used: bool = False

    def tick(self):
        self.tools += 1
        if self.tools > MAX_TOOLS:
            raise AnalysisFailure(
                "Source tool budget reached. Narrow the problem and retry.", "budget"
            )

    def emit(self, data):
        encoded = json.dumps(data, ensure_ascii=False)
        size = len(encoded.encode())
        if self.source_bytes + size > MAX_SOURCE_BYTES:
            raise AnalysisFailure(
                "Source context budget reached. Narrow the problem and retry.", "budget"
            )
        self.source_bytes += size
        return encoded

    def list_files(self, offset: int):
        self.tick()
        if offset < 0 or offset > 500:
            return self.emit({"error": "Invalid offset"})
        paths = sorted(self.files)
        return self.emit(
            {
                "files": paths[offset : offset + 40],
                "total": len(paths),
                "next_offset": offset + 40 if offset + 40 < len(paths) else None,
            }
        )

    def read_file(self, path: str, start: int, end: int):
        self.tick()
        if path not in self.files:
            return self.emit(
                {
                    "error": "File not in imported snapshot. Ask for the missing file instead of inventing its contents."
                }
            )
        lines = self.files[path].splitlines()
        if start < 1 or end < start or end - start >= 120 or start > len(lines):
            return self.emit({"error": "Request 1–120 existing lines."})
        selected = []
        size = 0
        for i in range(start - 1, min(end, len(lines))):
            line = lines[i]
            if len(line.encode()) > 6000 or size + len(line.encode()) > 8000:
                self.limitations.append(f"Line-range response truncated for {path}.")
                break
            selected.append({"line": i + 1, "text": line})
            size += len(line.encode())
        result = self.emit(
            {
                "path": path,
                "total_lines": len(lines),
                "lines": selected,
                "truncated": len(selected) < min(end, len(lines)) - start + 1,
            }
        )
        self.spans.setdefault(path, set()).update(x["line"] for x in selected)
        return result

    def search(self, query: str):
        self.tick()
        if not query.strip() or len(query) > 120:
            return self.emit({"error": "Use a literal search of 1–120 characters."})
        matches = []
        for path, content in sorted(self.files.items()):
            if query.casefold() in path.casefold():
                matches.append(
                    {"path": path, "line": 1, "text": "Filename match; read source for evidence."}
                )
            for i, line in enumerate(content.splitlines(), 1):
                if query.casefold() in line.casefold():
                    matches.append({"path": path, "line": i, "text": line[:180]})
                if len(matches) >= 20:
                    return self.emit({"matches": matches[:20], "truncated": True})
        return self.emit({"matches": matches, "truncated": False})

    def validate(self, result: Diagnosis):
        for finding in result.findings:
            for e in finding.evidence:
                if (
                    e.path not in self.files
                    or e.end_line < e.start_line
                    or e.end_line - e.start_line > 30
                ):
                    raise AnalysisFailure(
                        "Model returned invalid source references. Retry with a more focused error.",
                        "invalid_evidence",
                    )
                lines = self.files[e.path].splitlines()
                actual = "\n".join(lines[e.start_line - 1 : e.end_line])
                if (
                    e.end_line > len(lines)
                    or not set(range(e.start_line, e.end_line + 1)).issubset(
                        self.spans.get(e.path, set())
                    )
                    or e.quote != actual
                ):
                    raise AnalysisFailure(
                        "Model evidence did not match the source lines it read. No diagnosis was accepted.",
                        "invalid_evidence",
                    )
        for values in (
            result.questions,
            result.limitations,
            result.suggested_reproduction,
            result.verification_steps,
        ):
            if any(len(v) > 1500 for v in values):
                raise AnalysisFailure("Model output exceeded the result limit.", "invalid_output")
        if not result.findings and not result.questions:
            raise AnalysisFailure(
                "No grounded findings or clarifying questions were returned.", "invalid_output"
            )

    def stats(self):
        return {
            "model_calls": self.calls,
            "tool_calls": self.tools,
            "source_bytes": self.source_bytes,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "files_read": len(self.spans),
            "total_files": len(self.files),
            "specialists": self.specialists,
            "fallback_used": self.fallback_used,
        }
