import torch
import torch.nn as nn
from transformers import AutoModel

class IndoBERTHoaxClassifier(nn.Module):
    def __init__(self, model_name: str = "indobenchmark/indobert-base-p1", num_classes: int = 2, dropout_rate: float = 0.3):
        super(IndoBERTHoaxClassifier, self).__init__()
        
        # 1. Memuat Transformer IndoBERT Base P1
        self.indobert = AutoModel.from_pretrained(model_name)
        
        # 2. Teknik Layer Freezing: Bekukan Layer 1 sampai 8
        # Hanya melatih Layer 9-12 untuk mempercepat training dan mencegah overfitting
        for name, param in self.indobert.named_parameters():
            if any(f"encoder.layer.{i}." in name for i in range(8)):
                param.requires_grad = False

        # 3. Classification Head
        self.dropout = nn.Dropout(p=dropout_rate)
        self.classifier = nn.Linear(self.indobert.config.hidden_size, num_classes)

    def forward(self, input_ids, attention_mask=None, token_type_ids=None):
        outputs = self.indobert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids
        )
        
        # Ambil representasi vektor dari token pertama [CLS]
        cls_output = outputs.last_hidden_state[:, 0, :]
        
        # Alirkan ke Dropout dan Linear Classifier
        dropped = self.dropout(cls_output)
        logits = self.classifier(dropped)
        
        return logits