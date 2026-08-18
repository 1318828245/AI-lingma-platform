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


def test_shell_ls_long_listing_is_emulated(tmp_path):
    (tmp_path / "index.html").write_text("ok", encoding="utf-8")
    code, output = asyncio.run(run_command("ls -la", tmp_path, timeout=60))
    assert code == 0
    assert "index.html" in output


def test_shell_accepts_single_array_item_containing_full_command(tmp_path):
    (tmp_path / "index.html").write_text("ok", encoding="utf-8")
    code, output = asyncio.run(run_command(["ls -la"], tmp_path, timeout=60))
    assert code == 0
    assert "index.html" in output


def test_shell_runs_powershell_as_one_script(tmp_path):
    code, output = asyncio.run(
        run_command(
            ["powershell", "-Command", "Write-Output 'PS_OK'"],
            tmp_path,
            timeout=60,
        )
    )
    assert code == 0
    assert "PS_OK" in output


def test_shell_emulates_safe_rm_force(tmp_path):
    target = tmp_path / "check.js"
    target.write_text("ok", encoding="utf-8")
    code, output = asyncio.run(run_command(["rm", "-f", "check.js"], tmp_path, timeout=60))
    assert code == 0
    assert output == ""
    assert not target.exists()


def test_shell_supports_wc_and_head_chain(tmp_path):
    (tmp_path / "index.html").write_text(
        "<html>\n<body>\nrender()\n</body>\n</html>\n", encoding="utf-8"
    )
    code, output = asyncio.run(
        run_command(
            'wc -l index.html && node -e "const fs=require(\'fs\');const s=fs.readFileSync(\'index.html\',\'utf8\');if(!/render\\(\\)/.test(s))throw Error(\'bad\')"',
            tmp_path,
            timeout=60,
        )
    )
    assert code == 0
    assert "index.html" in output

    code, output = asyncio.run(
        run_command("find . -name index.html && head -c 300 index.html", tmp_path, timeout=60)
    )
    assert code == 0
    assert "<html>" in output


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


def test_shell_mode_preserves_list_argument_boundaries(tmp_path):
    code, output = asyncio.run(
        run_command(["python", "-c", "print('a b')"], tmp_path, timeout=60)
    )
    assert code == 0
    assert "a b" in output


def test_emulated_find_does_not_treat_name_pattern_as_path(tmp_path):
    (tmp_path / "a.js").write_text("", encoding="utf-8")
    (tmp_path / "b.css").write_text("", encoding="utf-8")
    code, output = asyncio.run(
        run_command(["find", ".", "-name", "*.js"], tmp_path, timeout=60)
    )
    assert code == 0
    assert "a.js" in output
    assert "b.css" not in output


def test_run_command_rejects_missing_workdir(tmp_path):
    with pytest.raises(BuildError, match="工作目录不存在"):
        asyncio.run(run_command(["pwd"], tmp_path / "missing", timeout=60))


def test_node_command_falls_back_when_async_subprocess_is_unavailable(tmp_path, monkeypatch):
    import app.services.sandbox as sandbox

    async def unsupported(*args, **kwargs):
        raise NotImplementedError

    monkeypatch.setattr(sandbox.asyncio, "create_subprocess_exec", unsupported)
    code, output = asyncio.run(
        run_command(["node", "-e", "console.log('fallback ok')"], tmp_path, timeout=60)
    )
    assert code == 0
    assert "fallback ok" in output
