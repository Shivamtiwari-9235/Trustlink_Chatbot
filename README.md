# TrustLink AI

TrustLink is a police and citizen legal information assistant for Indian statutory references. It combines local retrieval from a verified legal knowledge vault with Groq-hosted language generation, so the application can run on low-memory services such as Render's free tier or Streamlit Community Cloud.

> TrustLink provides informational assistance and statutory cross-referencing. It is not formal legal advice. For emergencies, contact the appropriate emergency service or a nearby police station.

## What It Does

- Answers questions about BNS, BNSS, MVA, IT Act, FIRs, bail, arrest procedure, citizen rights, and related topics.
- Searches the repository's verified legal vault using multilingual sentence embeddings and FAISS.
- Sends only retrieved legal context to Groq for a concise answer.
- Supports English, Hindi, and Hinglish queries.
- Applies guardrails that reject unsupported sources, fabricated sections, incomplete answers, and unsafe output.
- Keeps the embedding model and FAISS index cached during a Streamlit session.

## Architecture

```text
User query
	|
	v
Streamlit UI (src/app.py)
	|
	+--> LegalRetriever (src/retriever.py)
	|       +--> data/master_legal_vault.txt
	|       +--> multilingual embeddings
	|       +--> FAISS similarity search
	|
	+--> Groq API (llama-3.1-8b-instant)
			|
			v
		Guardrails and verified fallback
```

Retrieval, multilingual embeddings, and FAISS indexing remain local. Only response generation uses the Groq API. The legal vault is not uploaded to Groq as a standalone file; relevant retrieved context is included in each request.

## Requirements

- Python 3.10 or newer
- A Groq API key
- Internet access for installing dependencies, downloading the embedding model on first startup, and calling Groq

The generative model is not downloaded locally. This avoids the RAM usage caused by local PyTorch and Transformers inference.

## Local Setup

From the repository root:

```bash
python -m venv .venv
```

Activate the environment:

```powershell
.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a local environment file:

```powershell
Copy-Item .env.example .env
```


Start the application:

```bash
streamlit run src/app.py
```

The first startup downloads `paraphrase-multilingual-MiniLM-L12-v2` for retrieval. Later runs reuse the local model cache.

## Render Deployment

Create a Render Web Service connected to this repository with the repository root as its **Root Directory**. Leave the Root Directory field empty; do not set it to `src`.

The repository includes a `render.yaml` Blueprint configuration. You can deploy from that file, or configure the service manually with:

| Setting | Value |
| --- | --- |
| Environment | Python 3 |
| Build command | `pip install -r requirements.txt` |
| Start command | `streamlit run src/app.py --server.address 0.0.0.0 --server.port $PORT` |

Render should use Python 3.11.11, which is pinned in `.python-version` for compatibility with the embedding and FAISS dependencies. If the service was created with a different Root Directory, update it to the repository root and trigger a **Clear build cache & deploy**.

Add this environment variable in Render's Environment settings:

```text
GROQ_API_KEY=your_groq_api_key
```

Optional model override:

```text
TRUSTLINK_MODEL_ID=llama-3.1-8b-instant
```



## Streamlit Community Cloud

1. Select the GitHub repository and the `main` branch.
2. Set the main file to `src/app.py`.
3. Add `GROQ_API_KEY` under **Advanced settings > Secrets**.
4. Deploy the application.

If `GROQ_API_KEY` is missing, the retrieval layer can still load, but generated answers are disabled and the UI displays a configuration message.

## Testing

Run the real-world test suite from the repository root:

```bash
python -m pytest tests
```

To check Python syntax without starting Streamlit:

```bash
python -m py_compile src/app.py src/chatbot.py src/retriever.py
```

## Project Structure

```text
TrustLink/
├── data/
│   ├── master_legal_vault.txt     # Primary verified legal source
│   └── master_vault.txt            # Legacy fallback source
├── src/
│   ├── app.py                      # Streamlit interface
│   ├── chatbot.py                  # Groq generation and guardrails
│   └── retriever.py                # Embeddings and FAISS retrieval
├── tests/                          # RAG and real-world behavior tests
├── .env.example                    # Safe environment variable template
├── requirements.txt                # Lightweight runtime dependencies
└── README.md
```

## Emergency Contacts Shown In-App

- Police emergency: `112`
- Women helpline: `1091`
- Cyber crime helpline: `1930`
- Child helpline: `1098`

These numbers are provided for general reference. Confirm current local guidance when dealing with an emergency.
