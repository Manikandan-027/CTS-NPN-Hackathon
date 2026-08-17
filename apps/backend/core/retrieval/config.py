"""Configuration for semantic retrieval."""

DEFAULT_TOP_K = 20
MIN_TOP_K = 1
MAX_TOP_K = 100

# Chroma distance is converted into similarity by:
#
# similarity = 1 / (1 + distance)
#
# This gives:
# distance 0.0 -> similarity 1.0
# larger distance -> lower similarity
#
# NOTE:
# If the existing ChromaDB collection is configured with cosine
# distance and already returns cosine similarity, the conversion
# should instead be handled by the ChromaDB adapter.