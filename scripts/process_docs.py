################################################################################
## cisco-data-bridge-domain-index/scripts/process_docs.py
## Copyright (c) 2025 Jeff Teeter, Ph.D.
## Cisco Systems, Inc.
## Licensed under the Apache License, Version 2.0 (see LICENSE)
## Distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
################################################################################

# To create an index of domain summaries and API documentation files, this script processes the files, chunks them, generates embeddings, and indexes them.

import os
import json
import glob
import uuid
import logging
from dotenv import load_dotenv
from indexers.azure_indexer import AzureIndexer
from utils.chunking import chunk_file
from utils.embedding import embed_text  

# Load environment variables
load_dotenv()

# Create a logger
logger = logging.getLogger("azure")
logger.setLevel(logging.DEBUG)

# Create a file handler to write logs to a file
log_file = "azure_debug.log"
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)

# Create a formatter and set it for the handler
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)

print(f"Logging Azure SDK details to {log_file}")


def get_indexer(index_name):
    """Determines which backend to use and returns the appropriate indexer."""
    backend = os.getenv("VECTOR_BACKEND", "azure")
    if backend == "azure":
        return AzureIndexer(index_name)
    else:
        raise ValueError(f"Unsupported backend: {backend}")


def process_domain_summaries():
    """Processes and indexes domain summaries with manual embedding."""
    domain_index_name = os.getenv("AZURE_SEARCH_DOMAIN_INDEX", "domain-summaries-index")
    domain_indexer = get_indexer(domain_index_name)
    domain_indexer.create_index()

    domain_summaries_path = "domain_summaries/domain_summaries.json"
    with open(domain_summaries_path, "r", encoding="utf-8") as f:
        summaries = json.load(f)

    chunked_summaries = []
    for summary in summaries:
        if "content" not in summary:
            print(f"Warning: 'content' key missing in {summary}")
            continue

        chunks = chunk_file(summary["content"], chunk_size=1000, chunk_overlap=200)
        for chunk in chunks:
            # Generate an embedding for each chunk
            embedding_vector = embed_text(chunk)

            chunked_summaries.append({
                "id": summary["id"],  # Use the existing ID
                "content": chunk,
                "platform": summary.get("platform", "unknown"),
                "doc_type": summary.get("doc_type", "unknown"),
                # Store the embedding array
                "embedding": embedding_vector
            })

    domain_indexer.index_documents(chunked_summaries)
    print(f"Indexed {len(chunked_summaries)} domain summaries into {domain_index_name}.")


def process_api_docs():
    """
    Processes and indexes API documentation files with manual embedding.
    """
    api_docs_index_name = os.getenv("API_DOCS_INDEX_NAME", "api-docs-index")
    api_docs_indexer = get_indexer(api_docs_index_name)
    api_docs_indexer.create_index()

    platform_dirs = ["catalyst_center", "cisco_spaces", "meraki", "webex"]
    chunked_api_docs = []

    for platform_dir in platform_dirs:
        docs_path = os.path.join(platform_dir, "api-docs")
        specs_path = os.path.join(platform_dir, "api-specs")

        # Process markdown API docs
        for file_path in glob.glob(os.path.join(docs_path, "*.md")):
            platform = platform_dir
            doc_type = "api-docs"
            chunks = chunk_file(file_path, chunk_size=1000, chunk_overlap=200)
            for chunk in chunks:
                embedding_vector = embed_text(chunk)
                chunked_api_docs.append({
                    "id": str(uuid.uuid4()),
                    "content": chunk,
                    "platform": platform,
                    "doc_type": doc_type,
                    "embedding": embedding_vector
                })

        # Process JSON API specs
        for file_path in glob.glob(os.path.join(specs_path, "*.json")):
            platform = platform_dir
            doc_type = "api-specs"
            chunks = chunk_file(file_path, chunk_size=1000, chunk_overlap=200)
            for chunk in chunks:
                embedding_vector = embed_text(chunk)
                chunked_api_docs.append({
                    "id": str(uuid.uuid4()),
                    "content": chunk,
                    "platform": platform,
                    "doc_type": doc_type,
                    "embedding": embedding_vector
                })

    api_docs_indexer.index_documents(chunked_api_docs)
    print(f"Indexed {len(chunked_api_docs)} API documents into {api_docs_index_name}.")


if __name__ == "__main__":
    process_domain_summaries()
    process_api_docs()
