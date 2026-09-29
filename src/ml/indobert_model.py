# src/ml/indobert_model.py
import torch
import torch.nn as nn
from transformers import AutoConfig, AutoModel

class IndoBERTHoaxClassifier(nn.Module):
    def __init__(self, model_name="indobenchmark/indobert-base-p1", num_classes=2, dropout_rate=0.3):
        super(IndoBERTHoaxClassifier, self).__init__()
        
        # Muat konfigurasi arsitektur (hanya 1.5 KB, instan tanpa download model berat)
        self.config = AutoConfig.from_pretrained(model_name)
        # Bentuk kerangka model dari konfigurasi lokal
        self.indobert = AutoModel.from_config(self.config)
        
        self.dropout = nn.Dropout(p=dropout_rate)
        self.classifier = nn.Linear(self.config.hidden_size, num_classes)

    def forward(self, input_ids, attention_mask=None, token_type_ids=None):
        outputs = self.indobert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        cls_output = outputs.last_hidden_state[:, 0, :]
        dropped = self.dropout(cls_output)
        logits = self.classifier(dropped)
        return logits