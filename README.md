![Cisco Data Bridge Banner](assets/banner4.png)

This repository creates specialized vector databases (indexes) to support the **[Cisco Data Bridge AI Agent](https://github.com/APO-SRE/cisco-data-bridge-ai-agent)** by providing it with relevant domain information and detailed API documentation for various Cisco platforms. The solution is designed to work with multiple indexing backends (e.g., **Chroma**, **Elastic**, or **AI-Search**), enabling both on-prem and hybrid AI deployments.


**This repo is part of the [Cisco Data Bridge Project Suite](https://github.com/APO-SRE/cisco-data-bridge-project-suite).**



## Overview

### What This Project Does
1. **Generates Two Types of Indexes**:
   - **Domain Summaries**: A concise, high-level index that helps the AI Agent determine **which** Cisco platform (Meraki, Spaces, Catalyst Center, Webex Control Hub, etc.) is relevant to a given user query.
   - **Detailed API Docs & Specs**: A more extensive vector database that contains in-depth API information for each Cisco product. Once the AI Agent decides the domain is, for example, Meraki, it can query this index to retrieve the specific API references needed.

2. **Facilitates a Two-Stage Retrieval Process**:
   1. **Stage 1 - Domain Identification**: The AI Agent checks the **Domain Summaries** index to figure out which Cisco product(s) (Meraki, Catalyst Center, etc.) might be relevant.
   2. **Stage 2 - Detailed Lookup**: After identifying the correct domain(s), the AI Agent fetches deeper documentation from the **API Specs & Docs** index, ensuring it has everything needed to formulate calls or reason about the platform’s capabilities.

3. **Supports Multiple Backend Indexers**:
   - **Chroma**: A local vector store for quick prototyping or on-prem installations.
   - **Elastic**: Enterprise-grade search engine with vector or keyword-based indexing.
   - **AI-Search**: A specialized hybrid AI system indexing service.

By storing both a **lightweight domain index** and a **full-blown API reference** in vector format, the AI Agent can intelligently decide _what_ to do, then _how_ to do it—maximizing efficiency and accuracy.

## Repository Structure

Below is a high-level look at the contents of this repo:

```
cisco-data-bridge-domain-index/
├── LICENSE
├── README.md               # This README
├── catalyst_center/
│   ├── README
│   ├── api-docs/
│   │   └── catalyst-center-api.md
│   └── api-specs/
│       └── cisco-catalyst-center-intent-api-openai-3.0.1.json
├── cisco_spaces/
│   ├── README
│   ├── api-docs/
│   │   └── cisco-spaces-location-cloud-api.md
│   └── api-specs/
│       └── cisco-spaces-location-cloud-api-swagger-2.0.0.json
├── domain_summaries/
│   ├── README
│   └── domain_summaries.json
├── meraki/
│   ├── README
│   ├── api-docs/
│   │   └── meraki-dashbaord-api-and-camera-api.md
│   └── api-specs/
│       └── meraki-dashboard-openapi-3.0.1.json
├── webex/
│   ├── README
│   ├── api-docs/
│   │   └── TBD
│   └── api-specs/
│       └── TBD
├── scripts/
│   └── chunk_and_prepare.py
├── requirements.txt
└── ...
```

### Notable Folders

- **`domain_summaries/`**  
  Contains `domain_summaries.json`, which includes short, high-level descriptions of each Cisco product. This is the **first stop** for the AI Agent to decide relevance.

- **`catalyst_center/`, `cisco_spaces/`, `meraki/`, `webex/`**  
  Each subfolder stores detailed resources:
  - `api-docs/`: Markdown or textual references about the platform’s API usage.
  - `api-specs/`: Swagger/OpenAPI specifications describing endpoints, parameters, and models.

- **`scripts/`**  
  Contains `chunk_and_prepare.py` or other data preprocessing scripts that chunk large documents and embed them into one of the vector stores (Chroma, Elastic, AI-Search, etc.).

## How It Works

1. **Data Preprocessing**  
   - The `chunk_and_prepare.py` script (or similar pipelines) iterates over each directory (`catalyst_center/`, `meraki/`, etc.), splitting API docs into manageable text chunks.  
   - These chunks are then embedded (e.g., using an NLP model) and stored in a vector database.

2. **Domain Summaries**  
   - Summaries in `domain_summaries/domain_summaries.json` are indexed to quickly identify which Cisco platform is relevant.  
   - The AI Agent queries this summary index first, reducing the scope of the subsequent search.

3. **Detailed Lookups**  
   - Once the agent knows which platform is relevant—say, “Meraki” or “Catalyst Center”—it queries the corresponding vector index (in `meraki/api-docs/` or `catalyst_center/api-specs/`) to retrieve the full context.

4. **Integration With `cisco-data-bridge-ai-agent`**  
   - If the agent is configured for RAG (Retrieval-Augmented Generation), it performs the above retrieval steps automatically whenever it needs domain or API-level documentation.  
   - The indexes generated here are essential for providing the agent with the best knowledge needed to handle queries effectively.

## Usage

1. **Install Dependencies**  
   ```bash
   pip install -r requirements.txt
   ```
2. **Prepare or Update Indexes**  
   - Modify `chunk_and_prepare.py` as needed to specify your indexing backend (Chroma, Elastic, AI-Search, etc.).
   - Run the script:
     ```bash
     python scripts/chunk_and_prepare.py
     ```
   - This will generate or update the vector indexes with any new or modified files.

3. **Configure the Agent**  
   - In your [Cisco Data Bridge AI Agent](https://github.com/APO-SRE/cisco-data-bridge-ai-agent) repository, set `RAG_TYPE` in the environment (e.g., `RAG_TYPE=chroma`, `RAG_TYPE=elastic`, or `RAG_TYPE=ai_search`) to point to the indexes created here.

4. **Validate**  
   - Issue queries through the `cisco-data-bridge-ai-agent` frontend or API.  
   - Check logs to confirm the agent is referencing the domain summaries and then retrieving more detailed API docs.

## Roadmap & Extensibility

- **Additional Cisco Platforms**  
  - Simply add new folders (e.g., `duo_security/`) with `api-docs/` and `api-specs/` as needed.  
  - Update or create domain summaries in `domain_summaries.json`.

- **Support Additional Vector Stores**  
  - Extend or modify the indexing logic in `scripts/chunk_and_prepare.py` to create or update embeddings in your chosen storage.

- **Automated Updates**  
  - Integrate continuous integration pipelines to detect changes in doc/spec files, re-chunk them, and refresh indexes automatically.

## License

This project is licensed under the [Apache License 2.0](LICENSE). You are free to use, modify, and distribute the code, subject to the terms and conditions detailed in the Apache 2.0 license. This includes attribution requirements and ensuring that any modifications are properly documented. For more information, please refer to the full [license text](LICENSE).

---

**Note**: This repository focuses on constructing and maintaining the domain + doc indexes. The actual query flow and function-calling logic takes place in the **[cisco-data-bridge-ai-agent](https://github.com/APO-SRE/cisco-data-bridge-ai-agent)** project, which consumes these indexes to deliver contextually rich AI-driven responses.
