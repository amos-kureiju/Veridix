import torch
import torch.nn.functional as F
from transformers import AutoTokenizer
from lime.lime_text import LimeTextExplainer
import numpy as np
import os
import time
import re
from typing import Dict, Any

from src.core.config import settings
from src.ml.indobert_model import IndoBERTHoaxClassifier
from src.utils.political_guardrail import check_political_domain
from src.utils.text_preprocessor import clean_standard_text

class HoaxPredictor:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_path = settings.SAVED_MODEL_PATH
        
        print(f"--> [AI Core] Menyiapkan Tokenizer: {settings.MODEL_NAME_OR_PATH}...")
        self.tokenizer = AutoTokenizer.from_pretrained(settings.MODEL_NAME_OR_PATH)
        
        # 1. Memuat Bobot Model Nyata
        print(f"--> [AI Core] Memuat bobot model IndoBERT riil: {self.model_path}...")
        self.model = IndoBERTHoaxClassifier(settings.MODEL_NAME_OR_PATH, num_classes=2)
        
        if os.path.exists(self.model_path):
            self.model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            print("✅ [AI Core] Model IndoBERT Base P1 Asli Aktif di Memori!")
        else:
            raise FileNotFoundError(f"File model tidak ditemukan di {self.model_path}!")

        self.model.to(self.device)
        self.model.eval()

        # 2. Inisialisasi Mesin LIME Asli (Bukan Kamus Buatan)
        print("--> [AI Core] Menginisialisasi Mesin LIME Text Explainer Resmi...")
        self.explainer = LimeTextExplainer(
            class_names=["FAKTA", "HOAKS"],
            split_expression=r'\W+',
            random_state=42
        )

    def _predict_proba_batch(self, texts: list) -> np.ndarray:
        """
        Fungsi jembatan resmi untuk LIME:
        Menerima ratusan variasi teks hasil perturbasi, menjalankannya ke IndoBERT,
        dan mengembalikan matriks probabilitas murni dari model [P(Fakta), P(Hoaks)].
        """
        all_probs = []
        batch_size = 32  # Menggunakan batching agar cepat di CPU

        for i in range(0, len(texts), batch_size):
            batch_texts = [str(t) for t in texts[i:i + batch_size]]
            
            encodings = self.tokenizer(
                batch_texts,
                add_special_tokens=True,
                max_length=128,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )
            
            input_ids = encodings['input_ids'].to(self.device)
            attention_mask = encodings['attention_mask'].to(self.device)
            
            with torch.no_grad():
                logits = self.model(input_ids, attention_mask)
                probs = F.softmax(logits, dim=1).cpu().numpy()
                all_probs.extend(probs)

        return np.array(all_probs)

    def predict_and_explain(self, text: str) -> Dict[str, Any]:
        start_time = time.time()
        
        # 1. Guardrail Domain Politik
        is_political, entities = check_political_domain(text)
        
        # 2. Harmonisasi naskah (Lead Paragraph)
        words = text.split()
        if len(words) > 45:
            text_input = " ".join(words[:45])
            last_p = text_input.rfind('.')
            if last_p > len(text_input) * 0.4:
                text_input = text_input[:last_p + 1].strip()
            else:
                text_input = text_input.strip() + "."
        else:
            text_input = text

        cleaned_text = clean_standard_text(text_input)

        # 3. Prediksi Nyata Tunggal IndoBERT
        enc = self.tokenizer(
            cleaned_text,
            add_special_tokens=True,
            max_length=128,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        ).to(self.device)

        with torch.no_grad():
            logits = self.model(enc['input_ids'], enc['attention_mask'])
            probs = F.softmax(logits, dim=1).cpu().numpy()[0]
            pred_label = int(np.argmax(probs))

        prediction = "HOAX" if pred_label == 1 else "FACT"
        confidence = float(probs[pred_label])

        # 4. EKSEKUSI LIME ASLI (Membuat 100 Perturbasi Teks Nyata)
        # Menghitung bobot kontribusi kata murni berdasarkan respon model IndoBERT
        exp = self.explainer.explain_instance(
            cleaned_text,
            self._predict_proba_batch,
            num_features=10,
            num_samples=100  # 100 variasi teks cukup cepat di CPU (~1.5-2.5 detik)
        )

        lime_list = exp.as_list(label=1)  # Bobot terhadap kelas HOAKS
        
        tokens_explanation = []
        top_hoax, top_fact = [], []

        for word, weight in lime_list:
            influence = "HOAX" if weight > 0 else "FACT"
            tokens_explanation.append({
                "word": word,
                "weight": round(weight, 4),
                "influence": influence
            })
            if weight > 0:
                top_hoax.append({"word": word, "score": round(weight, 4)})
            else:
                top_fact.append({"word": word, "score": round(abs(weight), 4)})

        elapsed_time = round(time.time() - start_time, 2)

        return {
            "is_political": is_political,
            "prediction": prediction,
            "confidence_score": round(confidence, 4),
            "inference_time_seconds": elapsed_time,
            "extracted_text": text,
            "entities_detected": entities,
            "explanation": {
                "base_score": round(float(probs[1]), 4),
                "tokens": tokens_explanation,
                "top_hoax_words": top_hoax[:5],
                "top_fact_words": top_fact[:5]
            }
        }

predictor = HoaxPredictor()