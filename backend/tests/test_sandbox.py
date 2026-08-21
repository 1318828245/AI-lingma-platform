import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.services.sandbox import BuildError, _docker_run_args, _is_vite_project, _real_build, run_command


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


def _docker_settings():
    return SimpleNamespace(
        command_mode="docker",
        docker_binary="docker",
        docker_image="ai-lingma-sandbox:node20",
        docker_network="none",
        docker_workspace_path="/workspace",
        docker_user="sandbox",
        docker_memory_limit="768m",
        docker_cpu_limit=1.0,
        docker_pids_limit=256,
        docker_tmpfs_size="128m",
    )


def test_docker_run_args_apply_execution_isolation(tmp_path, monkeypatch):
    import app.services.sandbox as sandbox

    monkeypatch.setattr(sandbox, "get_settings", _docker_settings)
    args = _docker_run_args(["node", "--version"], tmp_path, "ai-lingma-run-test")

    assert args[:5] == ["docker", "run", "--rm", "--init", "--pull=never"]
    assert ["--network", "none"] == args[args.index("--network"):args.index("--network") + 2]
    assert "--read-only" in args
    assert ["--cap-drop", "ALL"] == args[args.index("--cap-drop"):args.index("--cap-drop") + 2]
    assert ["--security-opt", "no-new-privileges"] == args[args.index("--security-opt"):args.index("--security-opt") + 2]
    assert "type=bind,src=" + str(tmp_path.resolve()) + ",dst=/workspace" in args
    assert args[-3:] == ["ai-lingma-sandbox:node20", "node", "--version"]


def test_docker_mode_delegates_non_emulated_command(tmp_path, monkeypatch):
    import app.services.sandbox as sandbox

    called = []

    async def fake_docker(command, cwd, timeout=300):
        called.append((command, cwd, timeout))
        return 0, "container ok\n"

    monkeypatch.setattr(sandbox, "get_settings", _docker_settings)
    monkeypatch.setattr(sandbox, "_run_docker_command", fake_docker)
    code, output = asyncio.run(run_command(["node", "--version"], tmp_path, timeout=45))
    assert (code, output) == (0, "container ok\n")
    assert called == [(["node", "--version"], tmp_path.resolve(), 45)]


def test_docker_mode_keeps_readonly_emulated_commands_local(tmp_path, monkeypatch):
    import app.services.sandbox as sandbox

    (tmp_path / "hello.txt").write_text("ok", encoding="utf-8")
    monkeypatch.setattr(sandbox, "get_settings", _docker_settings)
    code, output = asyncio.run(run_command(["cat", "hello.txt"], tmp_path, timeout=60))
    assert code == 0
    assert output == "ok\n"


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


def test_vite_project_is_detected_for_relative_preview_assets(tmp_path):
    (tmp_path / "package.json").write_text(
        '{"scripts":{"build":"vite build"},"devDependencies":{"vite":"^5"}}',
        encoding="utf-8",
    )
    assert _is_vite_project(tmp_path)


def test_real_vite_build_uses_relative_asset_base(tmp_path, monkeypatch):
    import app.services.sandbox as sandbox

    (tmp_path / "package.json").write_text(
        '{"scripts":{"build":"vite build"},"devDependencies":{"vite":"^5"}}',
        encoding="utf-8",
    )
    (tmp_path / "node_modules").mkdir()
    calls = []

    async def fake_run(command, cwd, timeout=300):
        calls.append(command)
        return 0, "build ok\n"

    monkeypatch.setattr(sandbox, "run_command", fake_run)
    ok, _, errors = asyncio.run(_real_build(tmp_path, emit=None))
    assert ok and not errors
    assert calls == [["npm", "run", "build", "--", "--base=./"]]
