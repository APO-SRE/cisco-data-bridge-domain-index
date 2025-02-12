################################################################################
## cisco-data-bridge-domain-index/scripts/indexers/elastic_indexer.py
## Copyright (c) 2025 Jeff Teeter, Ph.D.
## Cisco Systems, Inc.
## Licensed under the Apache License, Version 2.0 (see LICENSE)
## Distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
################################################################################

import os
from elasticsearch import Elasticsearch
from .base_indexer import BaseIndexer

class ElasticIndexer(BaseIndexer):
    def __init__(self, index_name: str):
        super().__init__(index_name)
        self.host = os.getenv("ELASTIC_HOST", "http://localhost:9200")
        self.user = os.getenv("ELASTIC_USER", "elastic")
        self.password = os.getenv("ELASTIC_PASSWORD", "changeme")
        self.client = Elasticsearch(self.host, http_auth=(self.user, self.password))
    
    def create_index(self):
        if not self.client.indices.exists(index=self.index_name):
            self.client.indices.create(index=self.index_name, body={
                "mappings": {
                    "properties": {
                        "content": {"type": "text"},
                    }
                }
            })
            print(f"Created Elasticsearch index {self.index_name}.")
        else:
            print(f"Elasticsearch index {self.index_name} already exists.")
    
    def index_documents(self, docs: list):
        for doc in docs:
            self.client.index(index=self.index_name, document=doc)
        print(f"Elasticsearch: Indexed {len(docs)} documents in {self.index_name}.")
