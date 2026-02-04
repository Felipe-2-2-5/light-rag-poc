import faiss
import numpy as np
import json
import os
# Support running both as script from src/ and imported via top-level
try:
    from config import FAISS_INDEX_PATH, META_PATH
except ImportError:
    from src.config import FAISS_INDEX_PATH, META_PATH

class FaissStore:
    def __init__(self, dim, index_path=FAISS_INDEX_PATH, meta_path=META_PATH):
        self.dim = dim
        self.index_path = index_path
        self.meta_path = meta_path
        self.index = None
        self.meta = {}
        if os.path.exists(index_path) and os.path.exists(meta_path):
            self.load()
        else:
            self.index = faiss.IndexHNSWFlat(dim, 32)  # HNSW, good for small demos

    def add(self, vectors, metadatas):
        # vectors: np.array shape (n, dim)
        start_id = self.index.ntotal
        self.index.add(vectors.astype('float32'))
        for i, m in enumerate(metadatas):
            self.meta[start_id + i] = m
        self.save()

    def search(self, qvec, k=5):
        if self.index.ntotal == 0:
            return []
        q = qvec.astype('float32').reshape(1, -1)
        D, I = self.index.search(q, k)
        results = []
        for dist, idx in zip(D[0], I[0]):
            if idx == -1:
                continue
            # JSON loads dict keys as strings, so try both int and str lookup
            meta = self.meta.get(int(idx)) or self.meta.get(str(idx))
            results.append((idx, float(dist), meta))
        return results

    def save(self):
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w", encoding="utf-8") as fh:
            json.dump(self.meta, fh, ensure_ascii=False, indent=2)

    def load(self):
        self.index = faiss.read_index(self.index_path)
        with open(self.meta_path, "r", encoding="utf-8") as fh:
            self.meta = json.load(fh)
