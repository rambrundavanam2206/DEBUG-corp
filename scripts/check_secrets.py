"""Small repository guard; not a replacement for a dedicated secret scanner."""
import re
import subprocess
from pathlib import Path

patterns = [
    re.compile(r"sb_secret_[A-Za-z0-9_-]{20,}"),
    re.compile(r"gsk_[A-Za-z0-9]{30,}"),
    re.compile(r"AIza[A-Za-z0-9_-]{30,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]
tracked = subprocess.check_output(["git", "ls-files", "-z"]).decode().split("\0")
violations = []
for name in filter(None, tracked):
    path = Path(name)
    if path.name.startswith('.env') and path.name != '.env.example':
        violations.append(name)
        continue
    if not path.is_file():
        continue
    content = path.read_text(errors='replace')
    if any(pattern.search(content) for pattern in patterns):
        violations.append(name)
if violations:
    raise SystemExit('Possible credentials in: ' + ', '.join(violations))
print('PASS: tracked files contain no matched secret keys or private env files.')
