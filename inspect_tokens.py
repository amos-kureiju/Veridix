# memuat checkpoint ckpt_ce_{seed}.pt di laptop dan memprediksi teks
import os, sys
import numpy as np
import torch, torch.nn as nn
from transformers import AutoTokenizer, AutoModel

MODEL_NAME = "indobenchmark/indobert-base-p1"
MAX_LEN, DROPOUT, FREEZE_LAYERS, BATCH = 128, 0.3, 8, 32
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class Clf(nn.Module):  # identik dengan colab_02_indobert.py

  def __init__(self):
    super().__init__()
    self.bert = AutoModel.from_pretrained(MODEL_NAME)
    for p in self.bert.embeddings.parameters():
      p.requires_grad = False
    for i in range(FREEZE_LAYERS):
      for p in self.bert.encoder.layer[i].parameters():
        p.requires_grad = False
    self.drop = nn.Dropout(DROPOUT)
    self.head = nn.Linear(self.bert.config.hidden_size, 2)

  def forward(self, ids, am):
    return self.head(
        self.drop(
            self.bert(
                input_ids=ids, attention_mask=am
            ).last_hidden_state[:, 0, :]
        )
    )


_TOK = None


def get_tokenizer():
  global _TOK
  if _TOK is None:
    _TOK = AutoTokenizer.from_pretrained(MODEL_NAME)
  return _TOK


def load_ckpt(path):
  """Bagian beku (embedding + layer 0-7) dimuat dari model pralatih; bagian terlatih dari file .pt."""
  m = Clf().to(DEVICE)
  sd = torch.load(path, map_location=DEVICE)
  missing, unexpected = m.load_state_dict(sd, strict=False)
  assert not unexpected, f"kunci tak dikenal: {unexpected[:3]}"
  m.eval()
  return m


def base_model_revision(m):
  """Revisi (commit) model pralatih yang dimuat; catat di protokol untuk reproduksibilitas."""
  return getattr(m.bert.config, "_commit_hash", None)


@torch.no_grad()
def predict_texts(model, texts, batch=BATCH):
  tok = get_tokenizer()
  texts = [str(t) for t in texts]
  preds, probs = [], []
  for i in range(0, len(texts), batch):
    e = tok(
        texts[i : i + batch],
        max_length=MAX_LEN,
        padding="max_length",
        truncation=True,
        return_tensors="pt",
    )
    lg = model(e["input_ids"].to(DEVICE), e["attention_mask"].to(DEVICE))
    preds.append(lg.argmax(1).cpu().numpy())
    probs.append(torch.softmax(lg, 1)[:, 1].cpu().numpy())
  return np.concatenate(preds), np.concatenate(probs)