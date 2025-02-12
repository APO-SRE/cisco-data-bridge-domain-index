################################################################################
## cisco-data-bridge-domain-index/scripts/utils/embedding.py
## Copyright (c) 2025 Jeff Teeter, Ph.D.
## Cisco Systems, Inc.
## Licensed under the Apache License, Version 2.0 (see LICENSE)
## Distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
################################################################################

import os
import openai
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

# A simple module-level counter
_embedding_count = 0

load_dotenv()

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=2, max=10))
def embed_text(text: str) -> list:
    """
    Generates an embedding vector for the provided text using Azure OpenAI.
    Retries on failure with exponential backoff.
    Tracks how many embeddings we've generated so far.
    """
    global _embedding_count
    _embedding_count += 1

    print(f"Generating embedding #{_embedding_count}...")

    azure_openai_key = os.getenv("AZURE_OPENAI_EMBEDDING_KEY")
    azure_openai_endpoint = os.getenv("AZURE_OPENAI_EMBEDDING_ENDPOINT")
    azure_openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    azure_openai_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")

    if not all([azure_openai_key, azure_openai_endpoint, azure_openai_api_version, azure_openai_deployment]):
        raise ValueError("Missing Azure OpenAI env vars")

    openai.api_key = azure_openai_key
    openai.api_base = azure_openai_endpoint
    openai.api_type = "azure"
    openai.api_version = azure_openai_api_version

    try:
        resp = openai.Embedding.create(
            input=text,
            engine=azure_openai_deployment
        )
        embedding = resp["data"][0]["embedding"]
        print(f"Generated embedding #{_embedding_count} of length {len(embedding)}")
        return embedding
    except Exception as e:
        print(f"Embedding error: {e}")
        raise
