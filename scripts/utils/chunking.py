################################################################################
## cisco-data-bridge-domain-index/scripts/utils/chunking.py
## Copyright (c) 2025 Jeff Teeter, Ph.D.
## Cisco Systems, Inc.
## Licensed under the Apache License, Version 2.0 (see LICENSE)
## Distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND.
################################################################################
 
import os
import re
import uuid

from langchain.text_splitter import RecursiveCharacterTextSplitter

def chunk_file(filepath_or_text, chunk_size=1000, chunk_overlap=200):
    """
    Processes either a file path or raw text, splits into manageable chunks, and returns them.

    Args:
        filepath_or_text (str): Path to the file or raw text to process.
        chunk_size (int): Maximum size of each chunk.
        chunk_overlap (int): Overlap size between chunks.

    Returns:
        List[str]: List of text chunks.
    """
    text = ""
    # Check if the input is a file path
    if os.path.isfile(filepath_or_text):
        with open(filepath_or_text, 'r', encoding='utf-8') as f:
            text = f.read()
    else:
        # Treat the input as raw text
        text = filepath_or_text

    # Use LangChain's text splitter
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    return splitter.split_text(text)