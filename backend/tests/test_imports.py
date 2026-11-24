import asyncio
import io
import stat
import zipfile

import pytest
import respx
from fastapi import HTTPException

from app.services.imports import MAX_FILE, download_github, github_repo, inspect_zip


def archive(entries):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        for name, value in entries:
            z.writestr(name, value)
    return output.getvalue()


def test_cpp_and_skip_rules():
    files, skipped = inspect_zip(
        archive(
            [
                ("project/TICTAC.CPP", "class Queue {};"),
                ("project/.env", "secret"),
                ("project/node_modules/a.js", "generated"),
                ("project/image.png", b"\0"),
                ("project/src/b.py", "print(1)"),
            ]
        )
    )
    assert list(files) == ["TICTAC.CPP", "src/b.py"]
    assert len(skipped) == 3


@pytest.mark.parametrize(
    "path",
    ["../a.py", "/a.py", "a/../../b.py", "C:/a.py", "a\\b.py", "a//b.py", "a/./b.py", "a.zip"],
)
def test_reject_unsafe_entries(path):
    with pytest.raises(HTTPException):
        inspect_zip(archive([(path, "bad")]))


def test_symlink():
    link = zipfile.ZipInfo("a.py")
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(HTTPException):
        inspect_zip(archive([(link, "/etc/passwd")]))


def test_duplicate_case_paths():
    with pytest.raises(HTTPException):
        inspect_zip(archive([("a.py", "1"), ("A.py", "2")]))


def test_binary_and_large_file_skipped():
    files, skipped = inspect_zip(
        archive([("good.py", "1"), ("binary.py", b"\0"), ("large.py", "x" * (MAX_FILE + 1))])
    )
    assert list(files) == ["good.py"]
    assert len(skipped) == 2


def test_file_count_limit():
    with pytest.raises(HTTPException) as e:
        inspect_zip(archive([(f"{i}.py", "x") for i in range(501)]))
    assert e.value.status_code == 413


def test_expanded_limit():
    with pytest.raises(HTTPException) as e:
        inspect_zip(archive([("large.py", "x" * (31 * 1024 * 1024))]))
    assert e.value.status_code == 413


def test_invalid_zip():
    with pytest.raises(HTTPException):
        inspect_zip(b"not a zip")


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/a/b",
        "https://evil.test/a/b",
        "https://github.com@evil.test/a/b",
        "https://github.com/a/b/tree/main",
        "https://github.com/a/b?x=y",
        "https://github.com/a/..",
    ],
)
def test_github_url_allowlist(url):
    with pytest.raises(HTTPException):
        github_repo(url)


def test_git_suffix():
    assert github_repo("https://github.com/owner/repo.git") == ("owner", "repo")


@respx.mock
def test_commit_pinned_download():
    base = "https://api.github.com/repos/owner/repo"
    sha = "a" * 40
    respx.get(base).respond(200, json={"private": False, "default_branch": "main"})
    respx.get(base + "/commits/main").respond(200, json={"sha": sha})
    respx.get(f"https://codeload.github.com/owner/repo/zip/{sha}").respond(
        200, content=archive([("root/a.cpp", "int main(){}")])
    )
    data, branch, commit = asyncio.run(download_github("https://github.com/owner/repo", ""))
    assert branch == "main" and commit == sha
    assert "a.cpp" in inspect_zip(data)[0]


@respx.mock
def test_rate_limit():
    respx.get("https://api.github.com/repos/owner/repo").respond(403)
    with pytest.raises(HTTPException) as e:
        asyncio.run(download_github("https://github.com/owner/repo", ""))
    assert e.value.status_code == 429
