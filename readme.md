# TrustLink

TrustLink is a local, CPU-friendly legal information assistant for Indian police-related questions. It combines multilingual semantic retrieval, a small instruction-tuned language model, and deterministic guardrails to produce concise answers grounded in a verified legal knowledge vault.

TrustLink is an information and cross-reference tool. It is not an official police system, lawyer, or legal authority.

## What It Does

- Accepts English, Hindi, and Hinglish questions.
- Retrieves relevant sections from `data/master_vault.txt` with FAISS and multilingual embeddings.
- Uses `Qwen/Qwen2.5-0.5B-Instruct` by default to format a concise answer within Streamlit Cloud memory limits.
- Rejects unsupported or unsafe model output and falls back to verified context when possible.
- Provides emergency guidance for queries that are outside the verified knowledge base.
- Runs locally; no application API key is required.

## Architecture

1. `src/app.py` provides the Streamlit chat interface.
2. `src/chatbot.py` loads the language model, calls the retriever, and applies guardrails.
3. `src/retriever.py` loads the verified vault, creates an in-memory FAISS index, and reranks matches with keyword overlap.
4. `data/master_vault.txt` is the runtime source of legal content.

The embedding model and language model are downloaded from Hugging Face on first use and cached outside the repository. The application does not require a pre-built index file.

## Project Layout

```text
TrustLink/
├── data/
│   └── master_vault.txt       # Verified legal knowledge used at runtime
├── src/
│   ├── app.py                 # Streamlit entry point
│   ├── chatbot.py             # Model orchestration and guardrails
│   └── retriever.py           # FAISS retrieval and reranking
├── tests/
│   └── evaluate_rag.py        # Golden-query benchmark
├── .gitignore
├── README.md
└── requirements.txt
```

## Requirements

- Python 3.10 or newer
- 8 GB RAM recommended for local CPU inference
- Internet access for the first model download
- Windows, macOS, or Linux

## Installation

### Windows PowerShell

```powershell
git clone https://github.com/<your-account>/TrustLink.git
cd TrustLink
py -3.10 -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### macOS or Linux

```bash
git clone https://github.com/<your-account>/TrustLink.git
cd TrustLink
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Run the Application

```bash
streamlit run src/app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`.

For a terminal-only session:

```bash
python src/chatbot.py
```

The first startup can take several minutes because the embedding and language models must be downloaded and loaded into memory.

To use a larger compatible Hugging Face causal language model locally, set `TRUSTLINK_MODEL_ID` before starting Streamlit. The default model is intentionally kept small for Streamlit Community Cloud.

## Test and Evaluate

Run the golden-query benchmark from the project root:

```bash
python tests/evaluate_rag.py
```

The benchmark writes `evaluation_report.json`. This generated report is intentionally ignored by Git and should not be committed.

## Updating the Knowledge Vault

Edit `data/master_vault.txt` only after checking each entry against current official sources such as the BNS, BNSS, Motor Vehicles Act, Information Technology Act, applicable state rules, notifications, and court decisions.

Use one self-contained section per paragraph. Include the source law and the date checked. Preserve former-law mappings only when explicitly verified. Since the FAISS index is rebuilt in memory at startup, restart the application after changing the vault.

## Production Readiness Notes

- Review all legal content with a qualified legal professional before public deployment.
- Add authentication, rate limiting, request logging, monitoring, and a secure deployment configuration before exposing the app to the internet.
- Pin and regularly audit dependencies in `requirements.txt`.
- Do not commit model caches, virtual environments, generated reports, secrets, or unverified datasets.
- Provide a clear escalation path to a qualified lawyer, local police station, or emergency service.

## Legal and Safety Disclaimer

TrustLink provides general informational assistance and statutory cross-referencing only. It does not provide legal advice, determine guilt, replace a police officer or lawyer, or guarantee that a provision is current or applicable to a particular case. For an emergency in India, call `112`. For cyber financial fraud, call `1930` and report promptly at `https://cybercrime.gov.in`.
