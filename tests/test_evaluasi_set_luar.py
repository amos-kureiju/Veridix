"""External text/pair runner regressions: fake predictor and temporary CSV files only."""

import contextlib
from copy import deepcopy
from datetime import datetime, timezone
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import pandas as pd

import evaluasi_set_luar as runner
from src.ml import inference


ROOT = Path(__file__).resolve().parents[1]
TEXT = "Presiden dan pemerintah membahas anggaran bantuan sosial bersama anggota DPR untuk seluruh warga Indonesia."


def prediction(text, votes=0, **updates):
    decisions = {seed: int(index < votes) for index, seed in enumerate((42, 123, 999))}
    result = {
        "success": True,
        "status": "ambigu" if votes in (1, 2) else "dinilai",
        "label": "PERLU VERIFIKASI (SEED TIDAK SEPAKAT)" if votes in (1, 2) else
            "BERPOLA HOAKS" if votes == 3 else "TIDAK BERPOLA HOAKS",
        "decision_rule": "unanimous",
        "seed_decisions": decisions,
        "votes_hoax": f"{votes}/3",
        "agreement_ratio": max(votes, 3 - votes) / 3,
        "latency_seconds": 0.01,
        "teks_dinilai": text,
        "terpotong": False,
        "debug": {"prob_hoax_per_seed": {seed: 0.8 if vote else 0.2 for seed, vote in decisions.items()}},
    }
    result.update(updates)
    return result


class TestExternalTextRunner(unittest.TestCase):
    def setUp(self):
        self.context = tempfile.TemporaryDirectory()
        self.folder = Path(self.context.name)
        self.source = self.folder / "input.csv"
        self.output = self.folder / "report.csv"
        self.predictor = SimpleNamespace(
            rule="unanimous", backend=SimpleNamespace(audit={}),
            nilai=Mock(side_effect=lambda text, **_kwargs: prediction(text)),
        )

    def tearDown(self):
        self.context.cleanup()

    def save(self, rows):
        pd.DataFrame(rows).to_csv(self.source, index=False)

    def rows(self):
        return [
            {"id": "first", "text": TEXT + " Versi pertama.", "label": 0},
            {"id": "second", "text": TEXT + " Versi kedua.", "label": 0},
        ]

    def pair(self, kind="gaya"):
        rows = self.rows()
        for row, variant in zip(rows, ("v1", "v2")):
            row.update(
                pair_id="pair-1", group_id="claim-1", jenis_uji=kind, varian=variant,
                rujukan="https://evidence.example.test/fixture", bukti_label="Bukti fixture ditetapkan sebelum keluaran model.",
            )
        if kind == "isi":
            rows[0]["label"] = 1
        return rows

    @contextlib.contextmanager
    def engine(self):
        # Fence both binding styles, including a local import inside main().
        with patch.object(inference, "get_predictor", return_value=self.predictor) as lazy, \
                patch.object(runner, "get_predictor", return_value=self.predictor, create=True) as bound:
            yield lazy, bound

    def invoke(self, *extra, output=None, default_output=False):
        args = [str(self.source), *extra]
        if not default_output:
            args.extend(("--out", str(output or self.output)))
        previous = Path.cwd()
        try:
            os.chdir(self.folder)
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return runner.main(args)
        finally:
            os.chdir(previous)

    def read(self, path=None):
        return pd.read_csv(path or self.output)

    def assert_blank(self, value):
        self.assertTrue(pd.isna(value) or value == "", repr(value))

    def assert_bool(self, value, expected):
        self.assertEqual(str(value).lower(), str(expected).lower())

    def test_import_neither_parses_arguments_loads_predictor_nor_writes(self):
        code = (
            "import sys; from pathlib import Path; from unittest.mock import patch; "
            "sys.path.insert(0, sys.argv[1]); "
            "before=set(Path.cwd().iterdir()); "
            "guard=patch('src.ml.inference.get_predictor', side_effect=AssertionError('unexpected model load')); "
            "guard.start(); import evaluasi_set_luar as runner; "
            "assert callable(runner.main); "
            "assert set(Path.cwd().iterdir()) == before; guard.stop()"
        )
        completed = subprocess.run(
            [sys.executable, "-B", "-X", "utf8", "-c", code, str(ROOT), "--unknown"],
            cwd=self.folder, capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(completed.stdout, "")

    def test_stub_accepts_canonical_and_alias_columns_without_loading_real_model(self):
        for alias in (False, True):
            with self.subTest(alias=alias):
                rows = self.rows()
                if alias:
                    rows = [{"id": row["id"], "teks": row["text"], "label_acuan": row["label"]} for row in rows]
                self.save(rows)
                output = self.folder / f"stub-{alias}.csv"
                with self.engine() as providers:
                    self.assertEqual(self.invoke("--stub", "--by", "label", output=output), 0)
                    for provider in providers:
                        provider.assert_not_called()
                result = self.read(output)
                self.assertEqual(len(result), 2)
                self.assertEqual(set(result["eval_mode"]), {"stub"})
                self.assertEqual(result["text"].tolist(), [row["text"] for row in self.rows()])

    def test_invalid_interface_inputs_and_pairs_fail_before_loading(self):
        good = self.pair()
        cases = [
            ([], ()),
            ([{key: value for key, value in self.rows()[0].items() if key != "text"}], ()),
            ([self.rows()[0], self.rows()[0]], ()),
            ([{**self.rows()[0], "text": "   "}], ()),
            ([{**self.rows()[0], "label": 2}], ()),
            ([{**self.rows()[0], "label": None}], ()),
            ([good[0]], ("--pairs",)),
            ([good[0], {**good[1], "varian": "v1"}], ("--pairs",)),
            ([good[0], {**good[1], "group_id": "different"}], ("--pairs",)),
            ([good[0], {**good[1], "jenis_uji": "unknown"}], ("--pairs",)),
            ([good[0], {**good[1], "label": 1}], ("--pairs",)),
            ([{**row, "jenis_uji": "isi"} for row in good], ("--pairs",)),
            ([{**row, "bukti_label": " "} for row in good], ("--pairs",)),
            ([{key: value for key, value in row.items() if key != "pair_id"} for row in good], ("--pairs",)),
        ]
        for rows, flags in cases:
            with self.subTest(rows=rows, flags=flags):
                self.save(rows)
                with self.engine() as providers:
                    with self.assertRaises(SystemExit) as caught:
                        self.invoke(*flags)
                    self.assertEqual(caught.exception.code, 2)
                    for provider in providers:
                        provider.assert_not_called()
                self.assertFalse(self.output.exists())
        for raw in (
            "id,text,label,label\nR1,fixture,0,1\n",
            "id,text,label\nR1,unexpected,fixture,0\n",
        ):
            with self.subTest(raw=raw), self.engine() as providers:
                self.source.write_text(raw, encoding="utf-8")
                with self.assertRaises(SystemExit) as caught:
                    self.invoke()
                self.assertEqual(caught.exception.code, 2)
                for provider in providers:
                    provider.assert_not_called()
                self.assertFalse(self.output.exists())
        self.save(self.rows())
        for flags in (("--unknown",), ("--by",), ("--out",)):
            with self.subTest(flags=flags), self.engine() as providers:
                # Keep the incomplete option last rather than appending the normal --out.
                with self.assertRaises(SystemExit) as caught, contextlib.redirect_stderr(io.StringIO()):
                    runner.main([str(self.source), *flags])
                self.assertEqual(caught.exception.code, 2)
                for provider in providers:
                    provider.assert_not_called()

    def test_invalid_model_rows_are_blank_and_batch_continues(self):
        rows = self.rows() + [{"id": "last", "text": TEXT + " Versi terakhir.", "label": 0}]
        self.save(rows)
        broken = (
            None, {}, RuntimeError("fixture model failure"),
            prediction(rows[1]["text"], success=False),
            prediction(rows[1]["text"], label="unknown"),
            prediction(rows[1]["text"], votes_hoax="3/3"),
            prediction(rows[1]["text"], seed_decisions={42: 0.0, 123: 0, 999: 0}),
            prediction(rows[1]["text"], latency_seconds=-0.1),
            prediction(rows[1]["text"], debug={"prob_hoax_per_seed": {42: float("nan"), 123: 0.2, 999: 0.2}}),
        )
        for index, bad in enumerate(broken):
            with self.subTest(bad=bad):
                def classify(text, **_kwargs):
                    if text == rows[1]["text"]:
                        if isinstance(bad, Exception):
                            raise bad
                        return deepcopy(bad)
                    return prediction(text)

                self.predictor.nilai.side_effect = classify
                output = self.folder / f"failure-{index}.csv"
                with self.engine():
                    self.assertEqual(self.invoke(output=output), 1)
                result = self.read(output)
                self.assertEqual(result["status"].tolist(), ["dinilai", "gagal", "dinilai"])
                for field in ("pred", "label_model", "pred_42", "pred_123", "pred_999", "prob_42", "prob_123", "prob_999"):
                    self.assert_blank(result.iloc[1][field])
                self.assertTrue(str(result.iloc[1]["error"]).strip())

    def test_original_seed_decisions_survive_rounded_debug_at_threshold(self):
        self.save(self.rows()[:1])
        self.predictor.nilai.side_effect = lambda text, **_kwargs: prediction(
            text, debug={"prob_hoax_per_seed": {42: 0.5, 123: 0.2, 999: 0.2}},
        )
        with self.engine():
            self.assertEqual(self.invoke(), 0)
        row = self.read().iloc[0]
        self.assertEqual(row["pred_42"], 0)
        self.assertEqual(row["prob_42"], 0.5)
        self.assertEqual(row["votes_hoax"], "0/3")

    def test_gaya_pair_reports_flip_and_joint_correctness_on_both_rows(self):
        rows = self.pair()
        self.save(rows)
        self.predictor.nilai.side_effect = lambda text, **_kwargs: prediction(text, 0 if text == rows[0]["text"] else 3)
        with self.engine():
            self.assertEqual(self.invoke("--pairs"), 0)
        result = self.read()
        self.assertEqual(set(result["pasangan_status"]), {"dibandingkan"})
        for _, row in result.iterrows():
            self.assert_bool(row["label_berbalik"], True)
            self.assert_bool(row["keduanya_benar"], False)
            self.assert_bool(row["transisi_ambigu"], False)
            for seed in (42, 123, 999):
                self.assert_blank(row[f"delta_prob_{seed}"])
        self.assertIn("transisi_ambigu", result.columns)

    def test_isi_score_deltas_use_keliru_minus_benar_even_in_reversed_order(self):
        rows = self.pair("isi")
        self.save(list(reversed(rows)))
        self.predictor.nilai.side_effect = lambda text, **_kwargs: prediction(text, 3 if text == rows[0]["text"] else 0)
        with self.engine():
            self.assertEqual(self.invoke("--pairs"), 0)
        result = self.read()
        self.assertEqual(set(result["pasangan_status"]), {"dibandingkan"})
        for _, row in result.iterrows():
            self.assert_bool(row["keduanya_benar"], True)
            for seed in (42, 123, 999):
                self.assertAlmostEqual(row[f"delta_prob_{seed}"], 0.6)

    def test_pair_metrics_keep_ambiguity_failed_and_truncated_sides_distinct(self):
        rows = self.pair()
        self.save(rows)
        cases = (
            ("ambiguous", prediction(rows[1]["text"], 1), "dibandingkan", 0),
            ("truncated", prediction(rows[1]["text"], 3, terpotong=True), "tidak_dibandingkan", 0),
            ("unknown_truncation", prediction(rows[1]["text"], 3, terpotong=None), "tidak_dibandingkan", 0),
            ("collapsed_change", prediction(rows[0]["text"], 3), "tidak_dibandingkan", 0),
            ("failed", {}, "tidak_dibandingkan", 1),
        )
        for name, second, pair_status, code in cases:
            with self.subTest(case=name):
                self.predictor.nilai.side_effect = lambda text, **_kwargs: prediction(text) if text == rows[0]["text"] else deepcopy(second)
                output = self.folder / f"pair-{name}.csv"
                with self.engine():
                    self.assertEqual(self.invoke("--pairs", output=output), code)
                result = self.read(output)
                self.assertEqual(set(result["pasangan_status"]), {pair_status})
                for _, row in result.iterrows():
                    self.assert_blank(row["label_berbalik"])
                    self.assert_blank(row["keduanya_benar"])
                    if name == "ambiguous":
                        self.assert_bool(row["transisi_ambigu"], True)
                        self.assertEqual(row["transisi_status"], "dinilai->ambigu")
                    else:
                        self.assert_blank(row["transisi_ambigu"])

    def test_output_preflight_and_exclusive_publication_preserve_existing_files(self):
        self.save(self.rows())
        self.output.write_bytes(b"previous report remains unchanged")
        with self.engine() as providers:
            with self.assertRaises(SystemExit) as caught:
                self.invoke()
            self.assertEqual(caught.exception.code, 2)
            for provider in providers:
                provider.assert_not_called()
        self.assertEqual(self.output.read_bytes(), b"previous report remains unchanged")
        source_bytes = self.source.read_bytes()
        with self.engine() as providers:
            with self.assertRaises(SystemExit) as caught:
                self.invoke(output=self.source)
            self.assertEqual(caught.exception.code, 2)
            for provider in providers:
                provider.assert_not_called()
        self.assertEqual(self.source.read_bytes(), source_bytes)

        with patch.object(runner, "datetime", wraps=datetime) as clock:
            clock.now.return_value = datetime(2026, 11, 23, 10, 0, tzinfo=timezone.utc)
            with self.engine():
                before = set(self.folder.iterdir())
                self.assertEqual(self.invoke(default_output=True), 0)
            generated = [path for path in set(self.folder.iterdir()) - before if path.suffix == ".csv"]
            self.assertEqual(len(generated), 1)
            previous = generated[0].read_bytes()
            with self.engine() as providers:
                with self.assertRaises(SystemExit) as caught:
                    self.invoke(default_output=True)
                self.assertEqual(caught.exception.code, 2)
                for provider in providers:
                    provider.assert_not_called()
            self.assertEqual(generated[0].read_bytes(), previous)

        fresh = self.folder / "failed-publication.csv"
        before = set(self.folder.iterdir())
        with self.engine(), patch.object(runner.os, "link", side_effect=PermissionError("fixture publication failure")):
            self.assertEqual(self.invoke(output=fresh), 1)
        self.assertFalse(fresh.exists())
        self.assertEqual(set(self.folder.iterdir()), before)


if __name__ == "__main__":
    unittest.main()
