"""Bounded source inspection. Never extract or execute untrusted archives."""

import io
import re
import stat
import zipfile
from pathlib import PurePosixPath
from urllib.parse import quote, urlsplit

import httpx
from fastapi import HTTPException

MAX_ARCHIVE = 10 * 1024 * 1024
MAX_EXPANDED = 30 * 1024 * 1024
MAX_FILE = 500 * 1024
MAX_BUNDLE = 45 * 1024 * 1024
SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    "vendor",
    "__macosx",
}
EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".html",
    ".css",
    ".scss",
    ".md",
    ".txt",
    ".toml",
    ".yaml",
    ".yml",
    ".sql",
    ".c",
    ".cpp",
    ".cc",
    ".cxx",
    ".h",
    ".hpp",
    ".java",
    ".go",
    ".rs",
    ".sh",
    ".xml",
    ".ini",
    ".cfg",
    ".vue",
    ".svelte",
    ".cs",
    ".rb",
    ".php",
}
ARCHIVES = {".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar"}


def inspect_zip(data: bytes):
    if len(data) > MAX_ARCHIVE:
        raise HTTPException(413, "Archive exceeds 10 MB.")
    files, skipped, seen = {}, [], set()
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            entries = archive.infolist()
            if len(entries) > 3000 or sum(i.file_size for i in entries) > MAX_EXPANDED:
                raise HTTPException(413, "Archive exceeds 3,000 entries or 30 MB expanded.")
            # Strip one common enclosing directory (GitHub archives have one).
            names = [i.filename for i in entries if not i.is_dir()]
            root = (
                names[0].split("/")[0] + "/"
                if names
                and all("/" in n for n in names)
                and len({n.split("/")[0] for n in names}) == 1
                else ""
            )
            for item in entries:
                raw = item.filename
                parts = raw.rstrip("/").split("/")
                mode = item.external_attr >> 16
                if (
                    raw.startswith("/")
                    or "\\" in raw
                    or ":" in raw
                    or any(p in ("", ".", "..") for p in parts)
                    or any(ord(c) < 32 for c in raw)
                    or len(raw) > 500
                    or stat.S_ISLNK(mode)
                    or (stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR))
                    or item.flag_bits & 1
                ):
                    raise HTTPException(
                        422, "Archive contains unsafe paths, special files or encrypted entries."
                    )
                if item.is_dir():
                    continue
                path = raw[len(root) :] if root else raw
                if path.casefold() in seen:
                    raise HTTPException(
                        422, "Archive contains duplicate or case-conflicting paths."
                    )
                seen.add(path.casefold())
                lower = PurePosixPath(path.lower())
                if lower.suffix in ARCHIVES:
                    raise HTTPException(422, "Nested archives are not supported.")
                reason = None
                if any(p.lower() in SKIP_DIRS for p in parts):
                    reason = "Dependency or generated directory"
                elif (
                    lower.name.startswith(".env")
                    or lower.suffix in {".pem", ".key", ".p12", ".pfx"}
                    or lower.name
                    in {
                        "credentials.json",
                        "service-account.json",
                        "id_rsa",
                        "id_ed25519",
                        ".npmrc",
                        ".pypirc",
                    }
                ):
                    reason = "Potential credential file"
                elif item.file_size > MAX_FILE:
                    reason = "File exceeds 500 KB"
                elif lower.suffix not in EXTENSIONS and lower.name not in {
                    "dockerfile",
                    "makefile",
                    "requirements.txt",
                    ".gitignore",
                }:
                    reason = "Unsupported file type"
                if reason:
                    skipped.append({"path": path, "reason": reason})
                    continue
                content = archive.read(item)
                if len(content) > MAX_FILE:
                    raise HTTPException(413, "Expanded file exceeds limit.")
                try:
                    text = content.decode("utf-8-sig")
                    if "\0" in text:
                        raise UnicodeError()
                except UnicodeError:
                    skipped.append({"path": path, "reason": "Binary or non-UTF-8 content"})
                    continue
                files[path] = text
                if len(files) > 500:
                    raise HTTPException(413, "Project exceeds 500 source files.")
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, ValueError):
        raise HTTPException(422, "Invalid or unsupported ZIP archive.") from None
    if not files:
        raise HTTPException(422, "No supported UTF-8 source files found.")
    return files, skipped


def github_repo(url: str):
    parsed = urlsplit(url)
    if (
        parsed.scheme != "https"
        or parsed.netloc.lower() != "github.com"
        or parsed.query
        or parsed.fragment
    ):
        raise HTTPException(
            422, "Use https://github.com/owner/repository with no query or fragment."
        )
    match = re.fullmatch(r"/([A-Za-z0-9][A-Za-z0-9-]*)/([A-Za-z0-9_.-]+?)(?:\.git)?/?", parsed.path)
    if not match or match[2] in {".", ".."}:
        raise HTTPException(422, "Use the repository root URL; enter the branch separately.")
    return match[1], match[2]


async def download_github(url: str, branch: str):
    owner, repo = github_repo(url)
    try:
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            base = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": "DEBUGGER-project-import",
            }
            info = await client.get(base, headers=headers)
            check_github(info)
            metadata = info.json()
            if metadata.get("private"):
                raise HTTPException(422, "Only public repositories are supported.")
            branch = branch or metadata["default_branch"]
            commit = await client.get(f"{base}/commits/{quote(branch, safe='')}", headers=headers)
            check_github(commit)
            sha = commit.json()["sha"]
            if not re.fullmatch("[a-f0-9]{40}", sha):
                raise HTTPException(502, "GitHub returned an invalid commit.")
            chunks, size = [], 0
            async with client.stream(
                "GET", f"https://codeload.github.com/{owner}/{repo}/zip/{sha}"
            ) as response:
                check_github(response)
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > MAX_ARCHIVE:
                        raise HTTPException(413, "Repository archive exceeds 10 MB.")
                    chunks.append(chunk)
            return b"".join(chunks), branch, sha
    except (httpx.RequestError, KeyError, ValueError):
        raise HTTPException(503, "GitHub is temporarily unavailable. Please retry.") from None


def check_github(response):
    if response.status_code in (403, 429):
        raise HTTPException(429, "GitHub rate limit reached. Retry later.")
    if response.status_code == 404:
        raise HTTPException(422, "Public repository or branch not found.")
    if response.status_code != 200:
        raise HTTPException(
            502, "GitHub could not provide this repository. Check its URL and retry."
        )
