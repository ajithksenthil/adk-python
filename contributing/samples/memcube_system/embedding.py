from __future__ import annotations

import numpy as np

_ALPHABET = 'abcdefghijklmnopqrstuvwxyz'


def compute_embedding(text: str) -> list[float]:
  """Compute a simple character frequency embedding."""
  vec = [0.0] * len(_ALPHABET)
  for ch in text.lower():
    idx = _ALPHABET.find(ch)
    if idx >= 0:
      vec[idx] += 1
  arr = np.array(vec, dtype=np.float32)
  norm = np.linalg.norm(arr)
  if norm:
    arr /= norm
  return arr.tolist()
