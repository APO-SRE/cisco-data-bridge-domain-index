################################################################################
## cisco-data-bridge-domain-index/scripts/process_events.py
## Copyright (c) 2025 Jeff Teeter, Ph.D.
## Cisco Systems, Inc.
## Licensed under the Apache License, Version 2.0 (see LICENSE)
## Distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
################################################################################

# This script processes event data, generates embeddings, and indexes.

import os
import json
import logging
import uuid
from dotenv import load_dotenv
from indexers.azure_indexer import AzureIndexer  # Ensure azure_indexer.py has event_id in create_index()
from utils.embedding import embed_text

load_dotenv()

# Create a logger
logger = logging.getLogger("azure")
logger.setLevel(logging.DEBUG)

# Create a file handler to write logs to a file
log_file = "events_debug.log"
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)

# Create a formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)

# Add the file handler to the logger
logger.addHandler(file_handler)

print(f"Logging Azure SDK details to {log_file}")

def get_indexer(index_name):
    """Returns an AzureIndexer for the given index."""
    backend = os.getenv("VECTOR_BACKEND", "azure")
    if backend == "azure":
        return AzureIndexer(index_name)
    else:
        raise ValueError(f"Unsupported backend: {backend}")

def process_events():
    """
    Processes and indexes event data with manual embedding (one doc per event).

    We set each doc's 'id' to the event's event_id, ensuring the same
    unique ID is used in Azure. We also store structured data in
    'additional_info'. If a field doesn't exist or is "no_xxx", we omit it.
    """
    events_index_name = os.getenv("AZURE_SEARCH_EVENTS_INDEX", "events-index")
    events_indexer = get_indexer(events_index_name)

    # Create (or recreate) the index with complex field 'additional_info'
    events_indexer.create_index()

    events_path = "events/sample_events.json"
    with open(events_path, "r", encoding="utf-8") as f:
        events = json.load(f)

    docs = []
    doc_count = 0

    for event in events:
        # 1) Extract top-level fields
        event_type = event.get("event_type", "unknown_type")

        # 2) If there's an 'additional_info' field, read from there
        additional_info_raw = event.get("additional_info", {})

        zone_id = additional_info_raw.get("zone_id")
        timestamp = additional_info_raw.get("timestamp")
        camera_id = additional_info_raw.get("camera_id")
        building = additional_info_raw.get("building")
        floor = additional_info_raw.get("floor")
        location_str = additional_info_raw.get("location")
        cisco_ai = additional_info_raw.get("cisco_ai")

        recommended_actions = additional_info_raw.get("recommended_actions", [])
        urls_for_further_action = additional_info_raw.get("urls_for_further_action", [])
        extra_notes = additional_info_raw.get("extra_notes", [])

        # 3) Build 'content' text from event data (optional)
        #    e.g., using top-level zone_id, timestamp, camera from additional_info
        #    so the LLM sees it in plain text
        content_parts = []
        content_parts.append(f"Detected event: {event_type}")

        if zone_id:
            content_parts.append(f"in zone: {zone_id}")
        if timestamp:
            content_parts.append(f"at {timestamp}")
        if camera_id:
            content_parts.append(f"camera={camera_id}")

        # minimal fallback if no location
        location_line = []
        if building:
            location_line.append(building)
        if floor:
            location_line.append(f"floor {floor}")
        if location_str:
            location_line.append(location_str)

        if location_line:
            content_parts.append("Location: " + " / ".join(location_line))

        # join them all
        content = ". ".join(content_parts) + "."

        # 4) Build additional_info (omitting None)
        refined_info = {}
        if zone_id:
            refined_info["zone_id"] = zone_id
        if timestamp:
            refined_info["timestamp"] = timestamp
        if camera_id:
            refined_info["camera_id"] = camera_id
        if building:
            refined_info["building"] = building
        if floor:
            refined_info["floor"] = floor
        if location_str:
            refined_info["location"] = location_str
        if cisco_ai:
            refined_info["cisco_ai"] = cisco_ai

        if recommended_actions:
            refined_info["recommended_actions"] = recommended_actions
        if urls_for_further_action:
            refined_info["urls_for_further_action"] = urls_for_further_action
        if extra_notes:
            refined_info["extra_notes"] = extra_notes

        # 5) The doc's key in Azure is 'event_id'
        #    If event_id missing, fallback to a new random string
        event_id = event.get("event_id") or str(uuid.uuid4())

        # 6) Build final doc
        doc = {
            "id": event_id,    # <--- ensures doc key in Azure = event_id
            "event_id": event_id,
            "event_name": event.get("event", "Spaces"),
            "event_type": event_type,
            "content": content,
            "additional_info": refined_info
        }

        # 7) Generate embeddings from 'content' if needed
        doc["embedding"] = embed_text(doc["content"])

        docs.append(doc)
        doc_count += 1

    print(f"Preparing to upload {doc_count} documents to the index...")

    # Index them in one batch
    events_indexer.index_documents(docs)
    print(f"Indexed {doc_count} documents into '{events_index_name}'.")


if __name__ == "__main__":
    process_events()
