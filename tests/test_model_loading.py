"""Regresi pemuatan model: seluruh loader, Torch, dan bobot diganti tiruan."""

import os
import sys
import types
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

from src.ml import inference


class TestPretrainedCacheLoading(unittest.TestCase):
    def test_cached_artifacts_do_not_retry_online(self):
        loaded = object()
        loader = Mock()
        loader.from_pretrained.return_value = loaded

        self.assertIs(inference._load_pretrained(loader), loaded)
        loader.from_pretrained.assert_called_once_with(
            inference.MODEL_NAME,
            revision=inference.EXPECTED_BASE_REVISION,
            local_files_only=True,
        )

    def test_cache_miss_downloads_same_revision_and_format(self):
        loaded = object()
        loader = Mock()
        loader.from_pretrained.side_effect = [OSError("Cache belum lengkap"), loaded]

        self.assertIs(inference._load_pretrained(loader, use_safetensors=False), loaded)
        self.assertEqual(loader.from_pretrained.call_args_list, [
            call(inference.MODEL_NAME, revision=inference.EXPECTED_BASE_REVISION,
                 local_files_only=True, use_safetensors=False),
            call(inference.MODEL_NAME, revision=inference.EXPECTED_BASE_REVISION,
                 local_files_only=False, use_safetensors=False),
        ])

    def test_failed_download_is_not_replaced_with_another_model(self):
        loader = Mock()
        failure = OSError("Unduhan gagal")
        loader.from_pretrained.side_effect = [OSError("Cache kosong"), failure]

        with self.assertRaises(OSError) as raised:
            inference._load_pretrained(loader)
        self.assertIs(raised.exception, failure)
        self.assertEqual(loader.from_pretrained.call_count, 2)

    def test_other_loading_errors_do_not_trigger_network_retry(self):
        for failure in (RuntimeError("Bobot tidak cocok"), ValueError("Konfigurasi salah")):
            with self.subTest(error=type(failure).__name__):
                loader = Mock()
                loader.from_pretrained.side_effect = failure
                with self.assertRaises(type(failure)):
                    inference._load_pretrained(loader)
                self.assertEqual(loader.from_pretrained.call_count, 1)


class TestBackendPretrainedIntegration(unittest.TestCase):
    def make_modules(self, revision):
        class FakeModule:
            def to(self, _device):
                return self

            def eval(self):
                return self

        nn = types.ModuleType("torch.nn")
        nn.Module = FakeModule
        nn.Dropout = Mock()
        nn.Linear = Mock()
        torch = types.ModuleType("torch")
        torch.nn = nn
        torch.cuda = SimpleNamespace(is_available=lambda: False)
        torch.device = lambda device: device
        bert = SimpleNamespace(
            embeddings=SimpleNamespace(parameters=lambda: []),
            encoder=SimpleNamespace(layer=[SimpleNamespace(parameters=lambda: []) for _ in range(12)]),
            config=SimpleNamespace(hidden_size=768, _commit_hash=revision),
        )
        transformers = types.ModuleType("transformers")
        transformers.AutoTokenizer = Mock()
        transformers.AutoModel = Mock()
        transformers.AutoModel.from_pretrained.return_value = bert
        modules = {"torch": torch, "torch.nn": nn, "transformers": transformers}
        return modules, transformers

    def test_backend_pins_loaders_and_disables_only_optional_conversion(self):
        modules, transformers = self.make_modules(inference.EXPECTED_BASE_REVISION)
        offline_before = os.environ.get("HF_HUB_OFFLINE")
        with patch.dict(sys.modules, modules), patch.dict(os.environ, {"VERIDIX_ALLOW_UNVERIFIED": "0"}):
            os.environ.pop("DISABLE_SAFETENSORS_CONVERSION", None)
            with patch.object(inference.BackendIndoBERT, "_cek_pipeline") as check_pipeline, \
                    patch.object(inference.BackendIndoBERT, "_muat", return_value={}) as load_checkpoint:
                backend = inference.BackendIndoBERT()
                self.assertEqual(os.environ["DISABLE_SAFETENSORS_CONVERSION"], "1")
                self.assertEqual(os.environ.get("HF_HUB_OFFLINE"), offline_before)
                check_pipeline.assert_called_once_with()
                self.assertEqual(load_checkpoint.call_args_list, [call(42), call(123), call(999)])
                self.assertEqual(backend.audit["base_revision"], inference.EXPECTED_BASE_REVISION)
        transformers.AutoTokenizer.from_pretrained.assert_called_once_with(
            inference.MODEL_NAME, revision=inference.EXPECTED_BASE_REVISION, local_files_only=True
        )
        transformers.AutoModel.from_pretrained.assert_called_once_with(
            inference.MODEL_NAME, revision=inference.EXPECTED_BASE_REVISION,
            local_files_only=True, use_safetensors=False
        )

    def test_unexpected_base_revision_still_fails_before_checkpoints(self):
        modules, _ = self.make_modules("unexpected-revision")
        with patch.dict(sys.modules, modules), patch.dict(os.environ, {"VERIDIX_ALLOW_UNVERIFIED": "0"}), \
                patch.object(inference.BackendIndoBERT, "_cek_pipeline"), \
                patch.object(inference.BackendIndoBERT, "_muat") as load_checkpoint:
            with self.assertRaisesRegex(RuntimeError, "INTEGRITAS GAGAL"):
                inference.BackendIndoBERT()
            load_checkpoint.assert_not_called()


if __name__ == "__main__":
    unittest.main()
