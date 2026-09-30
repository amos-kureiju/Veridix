import torch
import torch.nn.functional as F
import numpy as np
from lime.lime_text import LimeTextExplainer
from typing import List, Dict, Any

class RealLimeExplainer:
    def __init__(self, model, tokenizer, device):
        self.model = model
        self.tokenizer = tokenizer
        self.device = device

        #Inisialisasi engine LIME resmi
        self.explainer = LimeTextExplainer(
            class_names=["FAKTA", "HOAKS"],
            split_expression=r'\W+',
            random_state=42
        )

    def _predict_proba_pipeline(self, texts: List[str]) -> np.ndarray:
        """
        Fungsi inferensi batch untuk LIME:
        Menjalankan ratusan variasi teks hasil perturbasi secara paralel (batch_size=32)
        agar inferensi di CPU laptop sangat cepat (<2 detik).
        """
        all_probs = []
        batch_size = 32

        for i in range(0, len(texts), batch_size):
            batch_chunk = [str(t) for t in texts[i:i + batch_size]]
            
            encodings = self.tokenizer(
                batch_chunk,
                add_special_tokens=True,
                max_length=128,
                padding='max_length',
                truncation=True,
                return_attention_mask=True,
                return_tensors='pt'
            )
            
            input_ids = encodings['input_ids'].to(self.device)
            attention_mask = encodings['attention_mask'].to(self.device)
            
            with torch.no_grad():
                logits = self.model(input_ids, attention_mask)
                probs = F.softmax(logits, dim=1).cpu().numpy()
                all_probs.extend(probs)

        return np.array(all_probs)

    def explain(self, clean_text: str, num_samples: int = 100) -> Dict[str, Any]:
        """
        Mengeksekusi perturbasi teks murni pada model IndoBERT
        dan mengekstrak bobot kontribusi kata (Feature Importance).
        """
        # Eksekusi LIME murni (bukan kamus buatan)
        exp = self.explainer.explain_instance(
            clean_text,
            self._predict_proba_pipeline,
            num_features=10,
            num_samples=num_samples
        )
        
        # Ambil bobot terhadap kelas HOAKS (label=1)
        raw_weights = exp.as_list(label=1)
        
        tokens_explanation = []
        top_hoax = []
        top_fact = []

        for word, weight in raw_weights:
            inf = "HOAX" if weight > 0 else "FACT"
            tokens_explanation.append({
                "word": word,
                "weight": round(weight, 4),
                "influence": inf
            })
            if weight > 0:
                top_hoax.append({"word": word, "score": round(weight, 4)})
            else:
                top_fact.append({"word": word, "score": round(abs(weight), 4)})

        return {
            "tokens": tokens_explanation,
            "top_hoax_words": top_hoax[:5],
            "top_fact_words": top_fact[:5]
        }