import asyncio
from pathlib import Path

import pytest

from app.services.sandbox import BuildError, run_command


def test_run_command_npm_version():
    code, output = asyncio.run(run_command(["npm", "--version"], Path("."), timeout=60))
    assert code == 0
    assert output.strip()


def test_run_command_dir_builtin(tmp_path):
    code, output = asyncio.run(run_command(["dir", "/b"], tmp_path, timeout=60))
    assert code == 0


def test_run_command_emulated_ls_cat_pwd_grep(tmp_path):
    (tmp_path / "hello.txt").write_text("你好 world\n", encoding="utf-8")

    code, out = asyncio.run(run_command(["ls"], tmp_path, timeout=60))
    assert code == 0 and "hello.txt" in out

    code, out = asyncio.run(run_command(["cat", "hello.txt"], tmp_path, timeout=60))
    assert code == 0 and "world" in out

    code, out = asyncio.run(run_command(["pwd"], tmp_path, timeout=60))
    assert code == 0 and str(tmp_path.resolve()) in out

    code, out = asyncio.run(
        run_command(["grep", "world", "hello.txt"], tmp_path, timeout=60)
    )
    assert code == 0 and "hello.txt:1:" in out


def test_sandbox_mode_whitelist_rejects():
    from app.services.sandbox import _run_sandbox_command

    with pytest.raises(BuildError):
        asyncio.run(
            _run_sandbox_command(["curl", "http://example.com"], Path("."), timeout=60)
        )


def test_shell_mode_supports_operators(tmp_path):
    code, output = asyncio.run(
        run_command(
            "node -e \"console.log('a')\" && echo ok",
            tmp_path,
            timeout=60,
        )
    )
    assert code == 0
    assert "a" in output
    assert "ok" in output


def test_run_command_single_string_command(tmp_path):
    (tmp_path / "index.html").write_text("line1\nline2\n", encoding="utf-8")
    code, output = asyncio.run(
        run_command(
            "node -e \"const fs=require('fs');console.log(fs.readFileSync('index.html','utf8').split('\\n').length)\"",
            tmp_path,
            timeout=60,
        )
    )
    assert code == 0
    assert "3" in output


def test_run_command_python3_fallback(tmp_path):
    code, output = asyncio.run(
        run_command(["python3", "-c", "print(1+1)"], tmp_path, timeout=60)
    )
    assert code == 0
    assert "2" in output
