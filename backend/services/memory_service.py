import chromadb
import json
import hashlib
from datetime import datetime
from core.config import get_settings

settings = get_settings()


class MemoryService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self.collection = self.client.get_or_create_collection(
            name="datawatch_v3",
            metadata={"hnsw:space": "cosine"}
        )

    def store(self, issue_type: str, dataset_meta: dict,
              suggested_fixes: list, outcome: str,
              confidence: float, dataset_id: str):
        doc_id  = hashlib.md5(f"{issue_type}{dataset_id}{datetime.now()}".encode()).hexdigest()
        document = (
            f"Issue: {issue_type}\n"
            f"Rows: {dataset_meta.get('rows',0)}, Cols: {dataset_meta.get('cols',0)}\n"
            f"Affected: {dataset_meta.get('columns_affected','unknown')}\n"
            f"Fix: {json.dumps(suggested_fixes)}\nOutcome: {outcome}"
        )
        self.collection.add(
            documents=[document],
            metadatas=[{
                "dataset_id":  dataset_id,
                "issue_type":  issue_type,
                "fixes":       json.dumps(suggested_fixes),
                "outcome":     outcome,
                "confidence":  confidence,
                "timestamp":   datetime.now().isoformat()
            }],
            ids=[doc_id]
        )

    def retrieve(self, issue_description: str, top_k: int = 5) -> list:
        try:
            count = self.collection.count()
            if count == 0:
                return []
            results = self.collection.query(
                query_texts=[issue_description],
                n_results=min(top_k, count),
                include=["documents", "metadatas", "distances"]
            )
            fixes = []
            for i, doc in enumerate(results["documents"][0]):
                meta       = results["metadatas"][0][i]
                similarity = round(1 - results["distances"][0][i], 3)
                if similarity < 0.3:
                    continue
                fixes.append({
                    "past_issue":      doc[:300],
                    "issue_type":      meta.get("issue_type"),
                    "suggested_fixes": json.loads(meta.get("fixes","[]")),
                    "outcome":         meta.get("outcome",""),
                    "confidence":      meta.get("confidence", 0),
                    "similarity_score":similarity,
                    "timestamp":       meta.get("timestamp")
                })
            return fixes
        except Exception:
            return []
