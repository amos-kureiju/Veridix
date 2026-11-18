"""Regresi launcher/reload terisolasi: tanpa impor main, model, atau database."""

import ast
import importlib
import os
import shlex
import tempfile
import unittest
from contextlib import chdir
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock, patch

from click.testing import CliRunner
from uvicorn.config import Config
from uvicorn.supervisors.statreload import StatReload


ROOT = Path(__file__).resolve().parents[1]
uvicorn_main = importlib.import_module("uvicorn.main")


def documented_config(reload):
    """Parse perintah README melalui CLI asli, tetapi cegah server dijalankan."""
    for line in (ROOT / "README.md").read_text(encoding="utf-8").splitlines():
        if not line.startswith("python -m uvicorn main:app "):
            continue
        args = shlex.split(line)[3:]
        if ("--reload" in args) != reload:
            continue
        with patch.object(uvicorn_main, "run") as run:
            outcome = CliRunner().invoke(uvicorn_main.main, args)
        if outcome.exit_code != 0:
            raise AssertionError(outcome.output) from outcome.exception
        run.assert_called_once()
        options = dict(run.call_args.kwargs, log_config=None)
        options.pop("app_dir", None)  # Ditangani uvicorn.run sebelum membuat Config.
        return Config(*run.call_args.args, **options)
    raise AssertionError("Perintah backend yang diperlukan tidak ditemukan di README")


class TestBackendRuntime(unittest.TestCase):
    def test_main_entrypoint_uses_existing_app_without_reload_or_subprocess(self):
        tree = ast.parse((ROOT / "main.py").read_text(encoding="utf-8"))
        guard = next(
            node for node in tree.body
            if isinstance(node, ast.If)
            and ast.unparse(node.test) == "__name__ == '__main__'"
        )
        app = object()
        uvicorn_stub = ModuleType("uvicorn")
        uvicorn_stub.run = Mock()
        scope = {"__name__": "__main__", "app": app}
        with patch.dict("sys.modules", {"uvicorn": uvicorn_stub}):
            exec(compile(ast.Module(body=[guard], type_ignores=[]), "main.py", "exec"), scope)
        uvicorn_stub.run.assert_called_once()
        self.assertIs(uvicorn_stub.run.call_args.args[0], app)
        config = Config(*uvicorn_stub.run.call_args.args,
                        **dict(uvicorn_stub.run.call_args.kwargs, log_config=None))
        self.assertFalse(config.reload)
        self.assertFalse(config.use_subprocess)
        self.assertEqual(config.workers, 1)

    def test_documented_default_stays_single_process_with_worker_environment(self):
        with patch.dict(os.environ, {"WEB_CONCURRENCY": "4"}):
            config = documented_config(reload=False)
        self.assertFalse(config.reload)
        self.assertFalse(config.use_subprocess)
        self.assertEqual(config.workers, 1)

    def test_documented_reload_skips_venv_and_detects_backend_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            project = Path(temporary).resolve()
            source = project / "src"
            source.mkdir()
            backend = source / "route.py"
            backend.write_text("# backend fixture\n", encoding="utf-8")
            dependencies = project / ".venv" / "Lib" / "site-packages" / "paddle"
            dependencies.mkdir(parents=True)
            dependency = dependencies / "ptq_quantizer.py"
            dependency.write_text("# dependency fixture\n", encoding="utf-8")
            main = project / "main.py"
            main.write_text("# root fixture\n", encoding="utf-8")

            with chdir(project), patch.dict(os.environ, {"WEB_CONCURRENCY": "1"}):
                config = documented_config(reload=True)
            self.assertEqual(config.reload_dirs, [source])
            self.assertGreaterEqual(config.reload_delay, 1.0)
            self.assertFalse(config.loaded)
            watcher = StatReload(config, target=Mock(), sockets=[])
            watcher.pause = Mock()  # Uji pemindaian saja, tanpa menunggu atau memulai proses.
            resolve = Path.resolve

            def reject_dependency_scan(path, *args, **kwargs):
                if ".venv" in path.parts:
                    raise OSError(1450, "Simulated Windows resource exhaustion")
                return resolve(path, *args, **kwargs)

            with patch.object(Path, "resolve", reject_dependency_scan):
                self.assertEqual(list(watcher.iter_py_files()), [backend])
                self.assertIsNone(watcher.should_restart())
                changed = backend.stat().st_mtime + 2
                os.utime(dependency, (changed, changed))
                os.utime(main, (changed, changed))
                self.assertIsNone(watcher.should_restart())
                os.utime(backend, (changed, changed))
                self.assertEqual(watcher.should_restart(), [backend])


if __name__ == "__main__":
    unittest.main()
