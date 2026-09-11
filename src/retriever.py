import os
import re

import faiss
from sentence_transformers import SentenceTransformer


class LegalRetriever:
    """Dense retriever backed by one verified legal vault only."""

    QUERY_STOPWORDS = {
        "and", "are", "for", "hai", "ka", "ke", "ki", "kya", "me", "par",
        "the", "this", "what", "with", "naye", "new", "law", "kanoon",
    }

    QUERY_ALIASES = {
        "document": "driving documents driving licence registration certificate insurance pollution under control PUC RC DL",
        "documents": "driving documents driving licence registration certificate insurance pollution under control PUC RC DL",
        "kagaz": "driving documents driving licence registration certificate insurance pollution under control PUC RC DL",
        "papers": "driving documents driving licence registration certificate insurance pollution under control PUC RC DL",
        "carry": "driving documents driving licence registration certificate insurance pollution under control PUC RC DL",
        "license": "driving licence documents RC insurance PUC",
        "licence": "driving licence documents RC insurance PUC",
        "rc": "registration certificate vehicle documents insurance PUC",
        "puc": "pollution under control certificate vehicle documents",
        "complaint": "fir police report",
        "report": "fir police complaint",
        "summon": "notice attendance bnss",
        "bulana": "notice attendance bnss",
        "arrest": "arrest grounds relative bail bnss",
        "girftar": "arrest grounds relative bail bnss",
        "raat": "woman arrest sunset sunrise bnss",
        "bail": "bailable non bailable anticipatory bail",
        "fraud": "cyber financial fraud 1930 it act",
        "scam": "cyber financial fraud 1930 it act",
        "rape": "sexual assault rape section 63 64 BNS former IPC 375 376 woman child",
        "balatkar": "rape sexual assault section 63 64 BNS former IPC 375 376",
        "sexual": "sexual harassment rape section 63 64 74 75 BNS",
        "theft": "chori section 303 BNS former IPC 379 stolen property mobile",
        "chori": "theft section 303 BNS former IPC 379 stolen property mobile",
        "murder": "hatya section 103 BNS former IPC 302 culpable homicide death",
        "hatya": "murder section 103 BNS former IPC 302",
        "assault": "hurt grievous hurt attempt murder section 109 115 117 BNS",
        "domestic": "domestic violence cruelty woman section 85 86 BNS former IPC 498A",
        "gharelu": "domestic violence cruelty woman section 85 86 BNS former IPC 498A",
        "hinsa": "domestic violence cruelty woman section 85 86 BNS former IPC 498A",
        "cruelty": "domestic violence cruelty woman section 85 86 BNS former IPC 498A",
        "pocso": "child sexual offence POCSO sections 3 4 7 8 mandatory reporting",
        "child": "POCSO child sexual assault sections 3 4 7 8",
        "drunk": "drunk driving section 185 Motor Vehicles Act alcohol",
        "kidnap": "kidnapping abduction section 137 BNS former IPC 363",
        "emergency": "112 police emergency",
    }

    def __init__(self, vault_path=None):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(base_dir, "data")
        self.vault_path = vault_path or self._find_vault()

        # Multilingual model: Hindi, Hinglish, English teeno ko natively samajhta hai
        print("Loading Multilingual Embedding Model (Hindi + English)...")
        self.embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        self.chunks = []
        self.index = None
        self.build_index()

    def _find_vault(self):
        requested_path = os.path.join(self.data_dir, "master_legal_vault.txt")
        if os.path.isfile(requested_path):
            return requested_path

        # Keep the current repository usable until the vault is renamed.
        legacy_path = os.path.join(self.data_dir, "master_vault.txt")
        if os.path.isfile(legacy_path):
            return legacy_path
        return requested_path

    def build_index(self):
        all_chunks = []
        if not os.path.isfile(self.vault_path):
            print(f"ERROR: Verified legal vault not found: {self.vault_path}")
            return

        with open(self.vault_path, "r", encoding="utf-8", errors="strict") as f:
            content = f.read()
        for block in content.split("\n\n"):
            clean = " ".join(block.split())
            if len(clean) > 30 and clean not in all_chunks:
                header = clean.split(":", 1)[0].strip()
                all_chunks.append(f"Statutory metadata: {header}. {clean}")

        self.chunks = all_chunks
        if not self.chunks:
            print("ERROR: No text files found in data/ folder!")
            return

        print(f"Indexing {len(self.chunks)} legal chunks for Hindi/English search...")
        embeddings = self.embedder.encode(
            self.chunks, 
            convert_to_numpy=True, 
            normalize_embeddings=True
        )
        self.index = faiss.IndexFlatIP(embeddings.shape[1])
        self.index.add(embeddings)
        print("FAISS Multilingual Index ready!\n")

    def retrieve(self, query, top_k=4, threshold=0.20):
        if self.index is None or len(self.chunks) == 0:
            return []

        normalized_query = query.lower()
        for term, expansion in self.QUERY_ALIASES.items():
            if re.search(rf"\b{re.escape(term)}\b", normalized_query):
                normalized_query += f" {expansion}"

        query_vec = self.embedder.encode([normalized_query], convert_to_numpy=True, normalize_embeddings=True)
        scores, indices = self.index.search(query_vec, len(self.chunks))
        query_terms = {
            term.lower()
            for term in re.findall(r"[a-zA-Z0-9]{3,}|[\u0900-\u097F]{3,}", normalized_query)
            if term.lower() not in self.QUERY_STOPWORDS
        }
        requested_sections = set(re.findall(r"\b(?:section|sec\.?)\s*(\d{1,3})\b", normalized_query))
        concept_markers = []
        if re.search(r"\b(?:rape|balatkar)\b", normalized_query, re.I):
            concept_markers.append(r"\bsection\s+(?:63|64)\b")
        if re.search(r"\b(?:domestic|gharelu|hinsa|cruelty)\b", normalized_query, re.I):
            concept_markers.append(r"\bsection\s+85\b.*\bbns\b")

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            chunk_terms = set(re.findall(r"[a-zA-Z0-9]{3,}|[\u0900-\u097F]{3,}", self.chunks[idx].lower()))
            lexical_overlap = len(query_terms & chunk_terms)
            reranked_score = float(score) + min(0.45, lexical_overlap * 0.15)
            matched_sections = set(re.findall(r"\b(?:section|sec\.?)\s*(\d{1,3})\b", self.chunks[idx].lower()))
            if requested_sections & matched_sections:
                reranked_score += 0.50
            if any(re.search(marker, self.chunks[idx], re.I) for marker in concept_markers):
                reranked_score += 0.60
            if re.search(r"\b(?:rape|balatkar)\b", normalized_query, re.I) and re.search(
                r"\bsection\s+64(?:\(1\))?\s+bns\b", self.chunks[idx], re.I
            ):
                reranked_score += 0.35
            if any(
                re.search(pattern, normalized_query, re.IGNORECASE)
                and re.search(pattern, self.chunks[idx], re.IGNORECASE)
                for pattern in (
                    r"\b(?:document|documents|kagaz|papers|carry|license|licence|rc|puc)\b",
                    r"\b(?:driving|drive|vehicle|gaadi|car|bike)\b",
                )
            ):
                reranked_score += 0.35
            if reranked_score >= threshold:
                results.append((self.chunks[idx], reranked_score))
        results.sort(key=lambda item: item[1], reverse=True)
        return results[:top_k]

if __name__ == "__main__":
    r = LegalRetriever()
    test_queries = [
        "घरेलू हिंसा की शिकायत कैसे करें?",
        "मोबाइल खोने पर क्या करें?",
        "cheating dhokhadhadi"
    ]
    for q in test_queries:
        print(f"\n--- Testing: {q} ---")
        for chunk, sc in r.retrieve(q):
            print(f"[{sc:.2f}] {chunk[:80]}...")