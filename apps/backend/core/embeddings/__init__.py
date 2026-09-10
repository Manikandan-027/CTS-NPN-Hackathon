"""
Embedding pipeline for the AI Incident RCA system.

Pipeline:

Incident description
    ↓
Tokenization
    ↓
Token-aware chunking
    ↓
all-MiniLM-L6-v2
    ↓
Chunk embeddings
    ↓
Mean pooling
    ↓
L2 normalization
    ↓
384-dimensional incident embedding
"""