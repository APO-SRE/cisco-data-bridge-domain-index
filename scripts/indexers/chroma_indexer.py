################################################################################
## cisco-data-bridge-domain-index/scripts/indexers/chroma_indexer.py
## Copyright (c) 2025 Jeff Teeter, Ph.D.
## Cisco Systems, Inc.
## Licensed under the Apache License, Version 2.0 (see LICENSE)
## Distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
################################################################################

import os
from chromadb.config import Settings
import chromadb
from .base_indexer import BaseIndexer

class ChromaIndexer(BaseIndexer):
    def __init__(self, index_name: str):
        super().__init__(index_name)
        self.chroma_db_dir = os.getenv("CHROMA_DB_DIR", "./chroma_db")
        self.client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=self.chroma_db_dir))
        self.collection = None

    def create_index(self):
        # Chroma automatically creates a collection if it doesn't exist
        self.collection = self.client.get_or_create_collection(name=self.index_name)
    
    def index_documents(self, docs: list):
        if not self.collection:
            self.create_index()
        ids = [doc["id"] for doc in docs]
        texts = [doc["content"] for doc in docs]
        self.collection.add(documents=texts, ids=ids, metadatas=docs)
        print(f"Chroma: Inserted {len(docs)} documents into collection {self.index_name}.")
