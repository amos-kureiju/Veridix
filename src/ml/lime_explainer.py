import torch
import torch.nn.functional as F
import numpy as np
from lime.lime_text import LimeTextExplainer
from typing import List, Dict, Any
import time

class LimeExplainer:
    def __init__(self, model, tokenizer, device):
        self.model     = model
        self.tokenizer = tokenizer
        self.device    = device

        # Inisialisasi LimeTextExplainer resmi dari library lime
        # split_expression memastikan LIME memisahkan kata dengan benar
        # untuk teks bahasa Indonesia
        self.explainer = LimeTextExplainer(
            class_names=["FAKTA", "HOAKS"],
            split_expression=r'\W+',
            random_state=42
        )
 
    def _predict_proba_pipeline(self, texts: List[str]) -> np.ndarray:
        """
        Fungsi wrapper yang dipanggil LIME untuk setiap batch perturbasi.
        LIME memanggil fungsi ini ratusan kali dengan variasi teks berbeda.
        Setiap variasi diproses oleh IndoBERT yang sudah di-fine-tune.
        Batch_size=32 untuk efisiensi di CPU.
        """
        all_probs = []
        batch_size = 32
 
        for i in range(0, len(texts), batch_size):
            batch_chunk = [str(t) for t in texts[i:i + batch_size]]
 
            encodings = self.tokenizer(
                batch_chunk,
                add_special_tokens=True,
                max_length=128,          # konsisten dengan training
                padding='max_length',
                truncation=True,
                return_attention_mask=True,
                return_tensors='pt'
            )
 
            input_ids      = encodings['input_ids'].to(self.device)
            attention_mask = encodings['attention_mask'].to(self.device)
 
            with torch.no_grad():
                logits = self.model(input_ids, attention_mask)
                probs  = F.softmax(logits, dim=1).cpu().numpy()
                all_probs.extend(probs)
 
        return np.array(all_probs)
 
    def explain(
        self,
        clean_text: str,
        num_samples: int = 100       # default web: 100 | notebook analisis: 500
    ) -> Dict[str, Any]:
        """
        Jalankan LIME pada satu teks bersih.
        num_samples = jumlah perturbasi teks yang dibuat LIME.
        Lebih tinggi = penjelasan lebih stabil, tapi lebih lambat.
        Untuk web produksi: 100 (~2-3 detik di CPU)
        Untuk analisis notebook: 500 (~8-10 detik)
        """
        start = time.time()
 
        # ── Eksekusi LIME murni ──────────────────────────────────────────
        exp = self.explainer.explain_instance(
            clean_text,
            self._predict_proba_pipeline,   # IndoBERT forward pass
            num_features=10,                # tampilkan 10 kata terpenting
            num_samples=num_samples         # jumlah perturbasi
        )
 
        elapsed = round(time.time() - start, 2)
 
        # ── Ambil bobot terhadap kelas HOAKS (label=1) ──────────────────
        raw_weights = exp.as_list(label=1)
 
        tokens_explanation = []
        top_hoax = []
        top_fact = []
 
        for word, weight in raw_weights:
            # weight positif  → kata mendorong prediksi ke HOAKS
            # weight negatif  → kata mendorong prediksi ke FAKTA
            influence = "HOAX" if weight > 0 else "FACT"
 
            tokens_explanation.append({
                "word":      word,
                "weight":    round(weight, 4),
                "influence": influence
            })
 
            if weight > 0:
                top_hoax.append({
                    "word":  word,
                    "score": round(weight, 4)
                })
            else:
                top_fact.append({
                    "word":  word,
                    "score": round(abs(weight), 4)
                })
 
        # Urutkan dari bobot tertinggi
        top_hoax.sort(key=lambda x: x["score"], reverse=True)
        top_fact.sort(key=lambda x: x["score"], reverse=True)
 
        return {
            "tokens":          tokens_explanation,
            "top_hoax_words":  top_hoax[:5],
            "top_fact_words":  top_fact[:5],
            "num_samples":     num_samples,      # untuk transparansi di log
            "inference_time":  elapsed           # catat waktu untuk Bab 3
        }
 
 
# ── Helper: panggil LIME dengan num_samples berbeda per konteks ─────────────
 
def explain_for_web(explainer: RealLimeExplainer, text: str) -> Dict[str, Any]:
    """Mode produksi web — cepat, num_samples=100."""
    return explainer.explain(text, num_samples=100)
 
 
def explain_for_analysis(explainer: RealLimeExplainer, text: str) -> Dict[str, Any]:
    """Mode analisis notebook — lebih stabil, num_samples=500."""
    return explainer.explain(text, num_samples=500)