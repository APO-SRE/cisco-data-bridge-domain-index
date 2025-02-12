################################################################################
## cisco-data-bridge-domain-index/scripts/indexers/azure_indexer.py
## Copyright (c) 2025 Jeff Teeter, Ph.D.
## Cisco Systems, Inc.
## Licensed under the Apache License, Version 2.0 (see LICENSE)
## Distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
################################################################################

import os
import openai
from dotenv import load_dotenv

from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchableField,
    SearchField,
    SimpleField,
    ComplexField,
    SearchFieldDataType,
    VectorSearch,
    VectorSearchProfile,
    HnswParameters,
    SemanticConfiguration,
    SemanticPrioritizedFields,
    SemanticField,
    SemanticSearch,
    CorsOptions,
    ScoringProfile,  # If you want custom scoring
)
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
from tenacity import retry, stop_after_attempt, wait_exponential

from .base_indexer import BaseIndexer

load_dotenv()

class AzureIndexer(BaseIndexer):
    """
    A unified class that can create multiple different index schemas
    depending on the index name (e.g. 'events-index', 'domain-summaries-index',
    'api-docs-index', or 'lob-...' indexes). Also handles manual embeddings if needed.
    """

    def __init__(self, index_name: str):
        super().__init__(index_name)

        self.endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        self.key = os.getenv("AZURE_SEARCH_KEY")

        print(f"AZURE_SEARCH_ENDPOINT: {self.endpoint}")
        print(f"INDEX_NAME: {index_name}")

        if not self.endpoint or not self.key:
            raise ValueError(
                "Azure Search endpoint or key not found. "
                "Please set AZURE_SEARCH_ENDPOINT and AZURE_SEARCH_KEY."
            )

        self.credential = AzureKeyCredential(self.key)
        self.index_client = SearchIndexClient(
            endpoint=self.endpoint,
            credential=self.credential,
            api_version=os.getenv("AZURE_SEARCH_API_VERSION", "2024-07-01")
        )
        self.search_client = None

    def create_index(self):
        """
        Creates the appropriate Azure Cognitive Search index by calling
        build_index_schema() based on self.index_name.
        If the index already exists, we skip creation.
        """
        print(f"Attempting to create/reuse index: {self.index_name}")
        # Build the index schema for the chosen index name
        index_schema = self.build_index_schema(self.index_name)

        try:
            existing_index = self.index_client.get_index(self.index_name)
            if existing_index:
                print(f"Index '{self.index_name}' already exists. Skipping creation.")
                self.search_client = SearchClient(
                    endpoint=self.endpoint,
                    index_name=self.index_name,
                    credential=self.credential,
                    api_version=os.getenv("AZURE_SEARCH_API_VERSION", "2024-07-01"),
                    logging_enable=True
                )
                return
        except ResourceNotFoundError:
            print(f"Index '{self.index_name}' does not exist. Creating index...")
        except HttpResponseError as e:
            print(f"Error checking index '{self.index_name}': {e}")
            raise

        try:
            self.index_client.create_index(index_schema)
            print(f"Index '{self.index_name}' created successfully.")
            print("Preparing to upload documents to the index...")
        except HttpResponseError as e:
            print(f"Failed to create index '{self.index_name}': {e}")
            raise

        # Initialize a SearchClient for the newly created index
        self.search_client = SearchClient(
            endpoint=self.endpoint,
            index_name=self.index_name,
            credential=self.credential,
            api_version=os.getenv("AZURE_SEARCH_API_VERSION", "2024-07-01"),
            logging_enable=True
        )

    def build_index_schema(self, index_name: str) -> SearchIndex:
        """
        Builds a SearchIndex schema, customizing fields for each index name.
        """
        EMBEDDING_DIM = 1536  # For text-embedding models



        if index_name.startswith("lob-"):
            """
            A flexible schema for LOB indexes. Re-uses 'content' as the main text field
            and 'embedding' for the vector field, so we don't break existing logic.
            
            Example fields:
              - id (key)
              - content (searchable text)
              - embedding (vector)
              - optional 'metadata' field if you want more properties
            """
            fields = [
                SearchableField(
                    name="id",
                    type=SearchFieldDataType.String,
                    key=True,
                    filterable=True,
                    searchable=True
                ),
                SearchableField(
                    name="content",
                    type=SearchFieldDataType.String,
                    searchable=True
                ),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    filterable=False,
                    sortable=False,
                    facetable=False,
                    vector_search_dimensions=EMBEDDING_DIM,
                    vector_search_profile_name="lobHnswProfile"
                ),
                # optional: a simple 'metadata' field for additional JSON or structure
                SearchableField(
                    name="metadata",
                    type=SearchFieldDataType.String,
                    searchable=True,
                    filterable=False
                )
            ]

            # We'll generate a semantic config name on the fly:
            semantic_config_name = f"{index_name}-semantic-config"
            semantic_config = SemanticConfiguration(
                name=semantic_config_name,
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=None,
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[]
                )
            )

            # Example of a custom scoring profile if you want
            # scoring_profile = ScoringProfile(
            #     name="myScoreProfile",
            #     text_weights={"content": 1.5}  # Weighted content field
            # )

            vector_search = VectorSearch(
                algorithms=[
                    {
                        "name": "lobHnsw",
                        "kind": "hnsw",
                        "parameters": HnswParameters(
                            m=4,
                            ef_construction=400,
                            ef_search=500,
                            metric="cosine"
                        )
                    }
                ],
                profiles=[
                    VectorSearchProfile(
                        name="lobHnswProfile",
                        algorithm_configuration_name="lobHnsw"
                    )
                ]
            )

            cors_options = CorsOptions(allowed_origins=["*"], max_age_in_seconds=60)

            return SearchIndex(
                name=index_name,
                fields=fields,
                vector_search=vector_search,
                semantic_search=SemanticSearch(configurations=[semantic_config]),
                cors_options=cors_options,
                # scoring_profiles=[scoring_profile] if you want a custom scoring profile
            )

        # existing logic for events, domain-summaries, api-docs
        if index_name == "events-index":
            fields = [
                SearchableField(
                    name="id",
                    type=SearchFieldDataType.String,
                    key=True,
                    filterable=True,
                    searchable=True
                ),
                SearchableField(
                    name="event_id",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    searchable=True
                ),
                SearchableField(
                    name="event_name",
                    type=SearchFieldDataType.String,
                    searchable=True
                ),
                SearchableField(
                    name="event_type",
                    type=SearchFieldDataType.String,
                    filterable=True,
                    searchable=True
                ),
                SearchableField(
                    name="content",
                    type=SearchFieldDataType.String,
                    searchable=True
                ),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    filterable=False,
                    sortable=False,
                    facetable=False,
                    vector_search_dimensions=EMBEDDING_DIM,
                    vector_search_profile_name="myHnswProfile"
                ),
                ComplexField(
                    name="additional_info",
                    fields=[
                        SearchableField(
                            name="zone_id",
                            type=SearchFieldDataType.String,
                            filterable=True,
                            searchable=True
                        ),
                        SearchField(
                            name="timestamp",
                            type=SearchFieldDataType.DateTimeOffset,
                            filterable=True,
                            sortable=True,
                            facetable=False
                        ),
                        SearchableField(
                            name="camera_id",
                            type=SearchFieldDataType.String,
                            filterable=True,
                            searchable=True
                        ),
                        SearchableField(
                            name="building",
                            type=SearchFieldDataType.String,
                            filterable=True,
                            searchable=True
                        ),
                        SearchableField(
                            name="floor",
                            type=SearchFieldDataType.String,
                            filterable=True,
                            searchable=True
                        ),
                        SearchableField(
                            name="location",
                            type=SearchFieldDataType.String,
                            filterable=True,
                            searchable=True
                        ),
                        SearchableField(
                            name="cisco_ai",
                            type=SearchFieldDataType.String,
                            filterable=True,
                            searchable=True
                        ),
                        SearchField(
                            name="recommended_actions",
                            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                            searchable=True,
                            filterable=False,
                            sortable=False,
                            facetable=False
                        ),
                        SearchField(
                            name="urls_for_further_action",
                            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                            searchable=True,
                            filterable=False,
                            sortable=False,
                            facetable=False
                        ),
                        SearchField(
                            name="extra_notes",
                            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
                            searchable=True,
                            filterable=False,
                            sortable=False,
                            facetable=False
                        )
                    ]
                )
            ]

            semantic_config = SemanticConfiguration(
                name="myEventsSemanticConfig",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="event_name"),
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[
                        SemanticField(field_name="event_type"),
                        SemanticField(field_name="event_id")
                    ]
                )
            )

            vector_search = VectorSearch(
                algorithms=[
                    {
                        "name": "myHnsw",
                        "kind": "hnsw",
                        "parameters": HnswParameters(
                            m=4,
                            ef_construction=400,
                            ef_search=500,
                            metric="cosine"
                        )
                    }
                ],
                profiles=[
                    VectorSearchProfile(
                        name="myHnswProfile",
                        algorithm_configuration_name="myHnsw"
                    )
                ]
            )

            cors_options = CorsOptions(allowed_origins=["*"], max_age_in_seconds=60)

            return SearchIndex(
                name=index_name,
                fields=fields,
                vector_search=vector_search,
                semantic_search=SemanticSearch(configurations=[semantic_config]),
                cors_options=cors_options
            )

        elif index_name == "domain-summaries-index":
            fields = [
                SearchableField(name="id", type=SearchFieldDataType.String, key=True, filterable=True),
                SearchableField(name="title", type=SearchFieldDataType.String, searchable=True),
                SearchableField(name="content", type=SearchFieldDataType.String, searchable=True),
                SearchableField(name="platform", type=SearchFieldDataType.String, filterable=True, searchable=True),
                SearchableField(name="doc_type", type=SearchFieldDataType.String, filterable=True, searchable=True),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    filterable=False,
                    sortable=False,
                    facetable=False,
                    vector_search_dimensions=EMBEDDING_DIM,
                    vector_search_profile_name="myHnswProfile"
                )
            ]
            semantic_config = SemanticConfiguration(
                name="mySummariesSemanticConfig",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[SemanticField(field_name="platform")]
                )
            )

        elif index_name == "api-docs-index":
            fields = [
                SearchableField(name="id", type=SearchFieldDataType.String, key=True, filterable=True, searchable=True),
                SearchableField(name="title", type=SearchFieldDataType.String, searchable=True),
                SearchableField(name="content", type=SearchFieldDataType.String, searchable=True),
                SearchableField(name="platform", type=SearchFieldDataType.String, filterable=True, searchable=True),
                SearchableField(name="doc_type", type=SearchFieldDataType.String, filterable=True, searchable=True),
                SearchField(
                    name="embedding",
                    type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                    searchable=True,
                    filterable=False,
                    sortable=False,
                    facetable=False,
                    vector_search_dimensions=EMBEDDING_DIM,
                    vector_search_profile_name="myHnswProfile"
                )
            ]
            semantic_config = SemanticConfiguration(
                name="myApiDocsSemanticConfig",
                prioritized_fields=SemanticPrioritizedFields(
                    title_field=SemanticField(field_name="title"),
                    content_fields=[SemanticField(field_name="content")],
                    keywords_fields=[SemanticField(field_name="platform")]
                )
            )

        else:
            raise ValueError(f"No schema logic defined for index '{index_name}'")

        vector_search = VectorSearch(
            algorithms=[
                {
                    "name": "myHnsw",
                    "kind": "hnsw",
                    "parameters": HnswParameters(
                        m=4,
                        ef_construction=400,
                        ef_search=500,
                        metric="cosine"
                    )
                }
            ],
            profiles=[
                VectorSearchProfile(
                    name="myHnswProfile",
                    algorithm_configuration_name="myHnsw"
                )
            ]
        )

        cors_options = CorsOptions(allowed_origins=["*"], max_age_in_seconds=60)

        return SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search,
            semantic_search=SemanticSearch(configurations=[semantic_config]),
            cors_options=cors_options
        )

    def index_documents(self, docs: list, batch_size: int = 500):
        """
        Upload documents with a manual 'embedding' array (if present).
        Each index has its own set of fields that must match what's in 'docs'.
        For LOB indexes, we expect docs to have { id, content, embedding, [metadata] } etc.
        """
        if not self.search_client:
            self.search_client = SearchClient(
                endpoint=self.endpoint,
                index_name=self.index_name,
                credential=self.credential,
                api_version=os.getenv("AZURE_SEARCH_API_VERSION", "2024-07-01"),
                logging_enable=True
            )

        total_docs = len(docs)
        print(f"Uploading {total_docs} documents to '{self.index_name}' in batches of {batch_size}...")

        for i in range(0, total_docs, batch_size):
            batch = docs[i : i + batch_size]
            batch_number = (i // batch_size) + 1

            if batch:
                sample_doc = batch[0]
                doc_id = sample_doc.get("id", "no_id")
                embedding_field = sample_doc.get("embedding")  # might be None
                embedding_length = len(embedding_field) if embedding_field else 0
                print(
                    f"Uploading batch {batch_number} with {len(batch)} docs. "
                    f"Sample doc => ID: {doc_id}, embedding length: {embedding_length}"
                )
            else:
                print(f"Uploading batch {batch_number}: (empty batch)")

            try:
                self.search_client.upload_documents(documents=batch)
                print(f"Batch {batch_number} upload completed.")
            except Exception as e:
                print(f"Error uploading batch {batch_number}: {e}")
                raise

        print(f"All {total_docs} documents have been uploaded successfully.")
