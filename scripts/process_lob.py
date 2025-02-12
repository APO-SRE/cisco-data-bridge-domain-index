################################################################################
## cisco-data-bridge-domain-index/scripts/process_lob.py
## Copyright (c) 2025 Jeff Teeter, Ph.D.
## Cisco Systems, Inc.
## Licensed under the Apache License, Version 2.0 (see LICENSE)
## Distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
################################################################################

# This script processes Line of Business (LOB) data, generates embeddings, and indexes them.

import os
import json
import glob
import uuid
from dotenv import load_dotenv
from indexers.azure_indexer import AzureIndexer
from utils.embedding import embed_text

load_dotenv()

def get_indexer(index_name):
    return AzureIndexer(index_name)

def process_lob():
    """
    Creates and populates a LOB index (e.g. 'lob-healthcare') from a folder:
      - LOB_INDEX_NAME (e.g. lob-healthcare)
      - LOB_INDEX_FOLDER_NAME (e.g. healthcare)
    We gather all *.json files from lob_samples/<folder> and combine them.
    
    Each JSON file is assumed to be a list of objects with fields
    that we can adapt into { id, content, metadata, embedding }.
    The flexible index schema in azure_indexer.py uses:
      - id -> key
      - content -> main text
      - embedding -> vector
      - metadata -> optional string
    """
    lob_index_name = os.getenv("LOB_INDEX_NAME", "lob-healthcare")
    folder_name = os.getenv("LOB_INDEX_FOLDER_NAME", "healthcare")

    print(f"Using LOB index name: {lob_index_name}")
    print(f"Using LOB folder: {folder_name}")

    # 1) Create the index if not exists
    indexer = get_indexer(lob_index_name)
    indexer.create_index()

    # 2) Build path to lob_samples/<folder_name>/
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # e.g. /home/jefteete/cisco-data-bridge-domain-index/scripts
    # go up one level => /home/jefteete/cisco-data-bridge-domain-index
    lob_path = os.path.join(base_dir, "lob_samples", folder_name)

    if not os.path.isdir(lob_path):
        print(f"ERROR: No directory found at {lob_path}")
        return

    # 3) Gather all *.json files in that folder
    json_files = glob.glob(os.path.join(lob_path, "*.json"))
    if not json_files:
        print(f"No .json files found in {lob_path}")
        return

    # 4) Load each file and combine them into a single list of records
    all_records = []
    for jf in json_files:
        print(f"Reading file: {jf}")
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
                # data might be a list or a dict; we assume list of objects
                if isinstance(data, list):
                    all_records.extend(data)
                elif isinstance(data, dict):
                    # in case it's a single record
                    all_records.append(data)
                else:
                    print(f"Skipping {jf}: not a list or dict.")
        except Exception as e:
            print(f"Error reading {jf}: {e}")

    if not all_records:
        print("No valid records found in the LOB folder. Exiting.")
        return

    # 5) Convert each record into { id, content, metadata, embedding }
    docs = []
    for record in all_records:
        # Fallback to a random UUID if no ID
        doc_id = str(record.get("id") or uuid.uuid4())

        # We'll assume each record might have some text fields that we can
        # combine as 'content'. Adjust as needed. For example:
        #   "content" -> put entire record in a big text block
        # Or if you have a known field like "name", "description", "notes",
        # you can combine them. We'll do a naive approach:
        # We'll join all string fields except "id" or "embedding".
        content_parts = []
        for k, v in record.items():
            if k.lower() in ["id", "embedding"]:
                continue
            if isinstance(v, str):
                content_parts.append(v)

        # Join the strings with a newline
        content_str = "\n".join(content_parts)

        # We'll store the entire record as JSON in "metadata"
        metadata_str = json.dumps(record, ensure_ascii=False)

        # 6) Generate embedding for "content_str"
        embedding = embed_text(content_str)

        doc = {
            "id": doc_id,
            "content": content_str,
            "embedding": embedding,
            "metadata": metadata_str
        }
        docs.append(doc)

    # 7) Upload them in batches
    print(f"Uploading {len(docs)} total LOB docs to index '{lob_index_name}'...")
    indexer.index_documents(docs, batch_size=100)
    print("Done uploading LOB docs.")

if __name__ == "__main__":
    process_lob()
