################################################################################
## cisco-data-bridge-domain-index/scripts/indexers/base_indexer.py
## Copyright (c) 2025 Jeff Teeter, Ph.D.
## Cisco Systems, Inc.
## Licensed under the Apache License, Version 2.0 (see LICENSE)
## Distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
################################################################################

class BaseIndexer:
    def __init__(self, index_name: str):
        self.index_name = index_name
    
    def create_index(self):
        """Create the index if it doesn't exist."""
        raise NotImplementedError
    
    def index_documents(self, docs: list):
        """Index a list of documents (dicts with text/content)."""
        raise NotImplementedError