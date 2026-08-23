# AI RAG Copilot

The project now includes a local Retrieval-Augmented Generation (RAG) Copilot.

## Architecture

```text
React Copilot UI
      |
      v
POST /api/copilot/chat
      |
      +--> Claim detection + PostgreSQL case context
      |
      +--> Policy retriever -> data/policies/*.txt
      |
      +--> Evidence retriever -> data/evidence/*.txt
      |
      v
Grounded context
      |
      v
LangChain ChatOllama
      |
      v
Llama 3.1 8B
      |
      v
Answer + retrieved source citations
```

## Local model

The default generation model is:

```text
llama3.1:8b
```

Start Ollama and pull it:

```bash
ollama serve
ollama pull llama3.1:8b
```

The chatbot also has a deterministic RAG fallback. If Ollama is unavailable, the UI still receives the retrieved policy/evidence instead of an invented answer.

## Embeddings

The base project uses a deterministic local embedding provider by default so the RAG demo can run without another model download. If desired, set:

```env
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
```

and run:

```bash
ollama pull nomic-embed-text
```

## Demo data

`backend/seed_demo.py` now seeds 24 synthetic claims.

There are also intentional duplicate-claim scenarios:

- CLM-1013 and CLM-1014 share synthetic patient/payer/amount patterns.
- CLM-1022 is another duplicate-claim example.
- CLM-1015 and CLM-1016 demonstrate repeated coding-error patterns.

All data is synthetic demo data.

## Example Copilot questions

- What evidence supports an appeal for CLM-1001?
- What is missing before we submit CLM-1005?
- Explain the payer policy for a prior authorization denial.
- Which cases look like duplicate claims?
- How much was recovered for CLM-1011?

## API

```http
POST /api/copilot/chat
```

Request:

```json
{
  "question": "What evidence supports an appeal for CLM-1001?",
  "claim_no": "CLM-1001",
  "history": []
}
```

The response includes:

- `answer`
- `claim_no`
- `model`
- `provider`
- `sources`
- `grounded`
