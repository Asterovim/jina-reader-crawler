#!/usr/bin/env python3
"""
Dify Metadata Importer for Crawled Content
Automatically imports markdown files with metadata into Dify knowledge base
"""

import os
import yaml
import re
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Dify configuration
DIFY_API_KEY = os.getenv('DIFY_API_KEY', '')
DIFY_DATASET_ID = os.getenv('DIFY_DATASET_ID', '')
DIFY_BASE_URL = os.getenv('DIFY_BASE_URL', 'https://api.dify.ai')
SKIP_EXISTING = os.getenv('SKIP_EXISTING', 'false').lower() == 'true'

# Knowledge Base Creation Settings
DIFY_KNOWLEDGE_NAME = os.getenv('DIFY_KNOWLEDGE_NAME', 'Jina Reader Crawl Results')
DIFY_KNOWLEDGE_DESCRIPTION = os.getenv('DIFY_KNOWLEDGE_DESCRIPTION', 'Knowledge base containing crawled content from Jina Reader')
DIFY_EMBEDDING_MODEL = os.getenv('DIFY_EMBEDDING_MODEL', 'mistral-embed')
DIFY_EMBEDDING_MODEL_PROVIDER = os.getenv('DIFY_EMBEDDING_MODEL_PROVIDER', 'mistralai')
DIFY_INDEXING_TECHNIQUE = os.getenv('DIFY_INDEXING_TECHNIQUE', 'high_quality')
DIFY_PERMISSION = os.getenv('DIFY_PERMISSION', 'only_me')

# Retrieval Model Configuration
DIFY_SEARCH_METHOD = os.getenv('DIFY_SEARCH_METHOD', 'hybrid_search')
DIFY_TOP_K = int(os.getenv('DIFY_TOP_K', '2'))
DIFY_SCORE_THRESHOLD_ENABLED = os.getenv('DIFY_SCORE_THRESHOLD_ENABLED', 'true').lower() == 'true'
DIFY_SCORE_THRESHOLD = float(os.getenv('DIFY_SCORE_THRESHOLD', '0.7'))
DIFY_RERANKING_ENABLED = os.getenv('DIFY_RERANKING_ENABLED', 'false').lower() == 'true'
DIFY_WEIGHTS = float(os.getenv('DIFY_WEIGHTS', '0.7'))

# Import paths - construct from OUTPUT_DIR
OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
CRAWL_RESULT_DIR = os.getenv('CRAWL_RESULT_DIR', f'crawl-result/{OUTPUT_DIR}')

# EU Compliance setting (affects metadata availability)
EU_COMPLIANCE = os.getenv('EU_COMPLIANCE', 'false').lower() == 'true'

import requests
import json

class DifyMetadataImporter:
    def __init__(self, api_key, dataset_id, base_url='https://api.dify.ai'):
        self.api_key = api_key
        self.dataset_id = dataset_id
        self.base_url = base_url.rstrip('/')
        self.metadata_fields = {}
        self.existing_documents_cache = None  # Cache for existing documents

        # Using direct API calls with requests

    def create_knowledge_base(self, name, description="", embedding_model="mistral-embed",
                             embedding_model_provider="zhipuai", indexing_technique="high_quality",
                             permission="only_me", search_method="hybrid_search", top_k=5,
                             score_threshold_enabled=True, score_threshold=0.7, reranking_enabled=False,
                             weights=0.7):
        """Create a new knowledge base (dataset)"""
        print(f"🏗️ Creating new knowledge base: {name}")

        url = f"{self.base_url}/v1/datasets"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        data = {
            "name": name,
            "description": description,
            "indexing_technique": indexing_technique,
            "permission": permission,
            "provider": "vendor",
            "embedding_model": embedding_model,
            "embedding_model_provider": embedding_model_provider,
            "retrieval_model": {
                "search_method": search_method,
                "reranking_enable": reranking_enabled,
                "top_k": top_k,
                "score_threshold_enabled": score_threshold_enabled,
                "score_threshold": score_threshold if score_threshold_enabled else None
            }
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code in [200, 201]:
                result = response.json()
                dataset_id = result.get('id')
                print(f"✅ Knowledge base created successfully!")
                print(f"   ID: {dataset_id}")
                print(f"   Name: {result.get('name')}")
                print(f"   Embedding Model: {result.get('embedding_model_provider')}/{result.get('embedding_model')}")
                print(f"   Search Method: {search_method}")
                print(f"   Top K: {top_k}")
                print(f"   Score Threshold: {'Enabled' if score_threshold_enabled else 'Disabled'}")
                if score_threshold_enabled:
                    print(f"   Score Threshold Value: {score_threshold}")
                if search_method == "hybrid_search":
                    print(f"   Weights (Semantic/Keyword): {weights}")
                print(f"   Reranking: {'Enabled' if reranking_enabled else 'Disabled'}")
                return dataset_id
            else:
                print(f"❌ Failed to create knowledge base: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error details: {error_detail}")
                except:
                    print(f"   Response text: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Error creating knowledge base: {e}")
            return None

    def update_retrieval_model(self, dataset_id, search_method="hybrid_search", top_k=5,
                              score_threshold_enabled=True, score_threshold=0.7,
                              reranking_enabled=False, weights=0.7,
                              embedding_model=None, embedding_model_provider=None):
        """Update retrieval model configuration for a dataset"""
        print(f"🔧 Updating retrieval model configuration...")

        url = f"{self.base_url}/v1/datasets/{dataset_id}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }

        retrieval_model = {
            "search_method": search_method,
            "reranking_enable": reranking_enabled,
            "top_k": top_k,
            "score_threshold_enabled": score_threshold_enabled,
            "score_threshold": score_threshold if score_threshold_enabled else None
        }

        # Set reranking_mode based on search method and weights
        if search_method == "hybrid_search" and weights is not None:
            retrieval_model["reranking_mode"] = "weighted_score"
        else:
            retrieval_model["reranking_mode"] = "reranking_model"

        # Add weights configuration for hybrid search
        if search_method == "hybrid_search":
            # Round weights to avoid floating point precision issues
            vector_weight = round(weights, 2)
            keyword_weight = round(1.0 - weights, 2)

            # Ensure embedding model info is provided for hybrid search
            if not embedding_model or not embedding_model_provider:
                print("⚠️ Warning: embedding_model and embedding_model_provider are required for weighted hybrid search")
                print("   Using default values...")
                embedding_model = embedding_model or "mistral-embed"
                embedding_model_provider = embedding_model_provider or "langgenius/mistralai/mistralai"

            retrieval_model["weights"] = {
                "weight_type": "customized",
                "vector_setting": {
                    "vector_weight": vector_weight,
                    "embedding_model_name": embedding_model,
                    "embedding_provider_name": embedding_model_provider
                },
                "keyword_setting": {
                    "keyword_weight": keyword_weight
                }
            }

        data = {
            "retrieval_model": retrieval_model
        }

        try:
            response = requests.patch(url, headers=headers, json=data)
            if response.status_code in [200, 201]:
                result = response.json()
                print(f"✅ Retrieval model updated successfully!")
                print(f"   Search Method: {search_method}")
                print(f"   Top K: {top_k}")
                print(f"   Score Threshold: {'Enabled' if score_threshold_enabled else 'Disabled'}")
                if score_threshold_enabled:
                    print(f"   Score Threshold Value: {score_threshold}")
                if search_method == "hybrid_search":
                    print(f"   Weighted Score: Enabled")
                    print(f"   Vector Weight: {round(weights, 2)}")
                    print(f"   Keyword Weight: {round(1.0 - weights, 2)}")
                print(f"   Reranking: {'Enabled' if reranking_enabled else 'Disabled'}")
                return True
            else:
                print(f"❌ Failed to update retrieval model: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error details: {error_detail}")
                except:
                    print(f"   Response text: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error updating retrieval model: {e}")
            return False

    def setup_metadata_fields(self):
        """Create necessary metadata fields for crawled content"""
        fields_to_create = [
            ("source_url", "string"),
            ("domain", "string"),
            ("crawl_date", "time"),
            ("description", "string")
        ]

        # Only add language field if not using EU compliance (EU API doesn't return metadata)
        if not EU_COMPLIANCE:
            fields_to_create.append(("language", "string"))

        print("🔧 Setting up metadata fields...")

        # First, get existing fields
        self._get_existing_metadata_fields()

        for name, field_type in fields_to_create:
            if name in self.metadata_fields:
                print(f"📋 Field already exists: {name}")
                continue

            try:
                # Direct API call
                field = self._create_metadata_field_api(name, field_type)
                if field:
                    self.metadata_fields[name] = field['id']
                    print(f"✅ Created field: {name} ({field_type})")

            except Exception as e:
                print(f"❌ Failed to create field {name}: {e}")
                # Try to get existing fields again in case it was created elsewhere
                self._get_existing_metadata_fields()

    def _create_metadata_field_api(self, name, field_type):
        """Create metadata field via direct API call"""
        url = f"{self.base_url}/v1/datasets/{self.dataset_id}/metadata"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            "type": field_type,
            "name": name
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code in [200, 201]:
                return response.json()
            else:
                print(f"❌ Failed to create field {name}: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error details: {error_detail}")
                except:
                    print(f"   Response text: {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error creating field {name}: {e}")
            return None

    def _get_existing_metadata_fields(self):
        """Get existing metadata fields"""
        try:
            # Direct API call
            url = f"{self.base_url}/v1/datasets/{self.dataset_id}/metadata"
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }

            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                for field in data.get('doc_metadata', []):
                    self.metadata_fields[field['name']] = field['id']
                    print(f"📋 Found existing field: {field['name']}")

        except Exception as e:
            print(f"⚠️ Error getting existing fields: {e}")

    def extract_frontmatter(self, file_path):
        """Extract YAML frontmatter from markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Match YAML frontmatter
            frontmatter_match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
            if frontmatter_match:
                frontmatter_yaml = frontmatter_match.group(1)
                markdown_content = frontmatter_match.group(2)

                metadata = yaml.safe_load(frontmatter_yaml)
                return metadata, markdown_content
            else:
                # No frontmatter, return empty metadata and full content
                return {}, content

        except Exception as e:
            print(f"❌ Error extracting frontmatter from {file_path}: {e}")
            return {}, ""

    def import_document_with_metadata(self, file_path):
        """Import a single markdown file with its metadata"""
        print(f"📄 Processing: {file_path}")

        # Extract metadata and content
        metadata, content = self.extract_frontmatter(file_path)

        if not content.strip():
            print(f"⚠️ Empty content in {file_path}, skipping")
            return None

        # Get document name from metadata or filename
        title = metadata.get('title', Path(file_path).stem)
        crawl_date = metadata.get('crawl_date', '')

        # Trim title if too long (reserve space for crawl_date suffix)
        if len(title) > 150:
            title = title[:147] + "..."

        # Create unique document name with title + crawl_date
        doc_name = f"{title} ({crawl_date})"

        try:
            # Check if document already exists
            existing_doc_id = self._find_existing_document(doc_name)
            if existing_doc_id:
                if SKIP_EXISTING:
                    print(f"⏭️ Document '{doc_name}' already exists, skipping...")
                    return existing_doc_id
                else:
                    print(f"🔄 Document '{doc_name}' already exists, replacing it...")
                    self._delete_document(existing_doc_id)

            # Import document with parent-child mode and full document as parent
            # Direct API call with parent-child configuration
            document_id = self._create_document_api(doc_name, content)

            if not document_id:
                print(f"❌ Failed to create document for {file_path}")
                return None

            print(f"✅ Created document: {doc_name} (ID: {document_id})")

            # Prepare metadata for assignment
            metadata_list = []
            for key, value in metadata.items():
                if key in self.metadata_fields:
                    metadata_list.append({
                        "id": self.metadata_fields[key],
                        "value": str(value),
                        "name": key
                    })

            # Assign metadata if any
            if metadata_list:
                self._update_document_metadata_api(document_id, metadata_list)

                print(f"✅ Assigned {len(metadata_list)} metadata fields")

            return document_id

        except Exception as e:
            print(f"❌ Error importing {file_path}: {e}")
            return None

    def _create_document_api(self, name, text):
        """Create document via direct API call with parent-child mode"""
        url = f"{self.base_url}/v1/datasets/{self.dataset_id}/document/create-by-text"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            "name": name,
            "text": text,
            "indexing_technique": "high_quality",
            "doc_form": "hierarchical_model",
            "process_rule": {
                "mode": "hierarchical",
                "rules": {
                    "pre_processing_rules": [
                        {
                            "id": "remove_extra_spaces",
                            "enabled": True
                        },
                        {
                            "id": "remove_urls_emails",
                            "enabled": False
                        }
                    ],
                    "segmentation": {
                        "separator": "\\n",
                        "max_tokens": 1024
                    },
                    "parent_mode": "full-doc",
                    "subchunk_segmentation": {
                        "separator": "\\n",
                        "max_tokens": 512,
                        "chunk_overlap": 50
                    }
                }
            }
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200:
                result = response.json()
                return result.get('document', {}).get('id')
            else:
                print(f"❌ Failed to create document: {response.status_code}")
                return None
        except Exception as e:
            print(f"❌ Error creating document: {e}")
            return None

    def _update_document_metadata_api(self, document_id, metadata_list):
        """Update document metadata via direct API call"""
        url = f"{self.base_url}/v1/datasets/{self.dataset_id}/documents/metadata"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {
            "operation_data": [{
                "document_id": document_id,
                "metadata_list": metadata_list
            }]
        }

        try:
            response = requests.post(url, headers=headers, json=data)
            if response.status_code != 200:
                print(f"⚠️ Failed to update metadata: {response.status_code}")
        except Exception as e:
            print(f"❌ Error updating metadata: {e}")

    def _load_existing_documents_cache(self):
        """Load all existing documents into cache for faster lookups"""
        if self.existing_documents_cache is not None:
            return  # Already loaded

        print("📋 Loading existing documents cache...")
        self.existing_documents_cache = {}

        try:
            url = f"{self.base_url}/v1/datasets/{self.dataset_id}/documents"
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }

            # Load all pages
            page = 1
            total_docs = 0
            while True:
                params = {'page': page, 'limit': 100}  # Larger page size for efficiency
                response = requests.get(url, headers=headers, params=params)

                if response.status_code != 200:
                    break

                data = response.json()
                documents = data.get('data', [])

                # Add documents to cache
                for doc in documents:
                    doc_name = doc.get('name')
                    doc_id = doc.get('id')
                    if doc_name and doc_id:
                        self.existing_documents_cache[doc_name] = doc_id
                        total_docs += 1

                # Check if there are more pages
                if not data.get('has_more', False):
                    break
                page += 1

            print(f"✅ Loaded {total_docs} existing documents into cache")

        except Exception as e:
            print(f"⚠️ Error loading documents cache: {e}")
            self.existing_documents_cache = {}

    def _find_existing_document(self, doc_name):
        """Find existing document by name using cache"""
        # Load cache if not already loaded
        if self.existing_documents_cache is None:
            self._load_existing_documents_cache()

        return self.existing_documents_cache.get(doc_name)

    def _delete_document(self, document_id):
        """Delete an existing document"""
        try:
            url = f"{self.base_url}/v1/datasets/{self.dataset_id}/documents/{document_id}"
            headers = {
                'Authorization': f'Bearer {self.api_key}'
            }

            response = requests.delete(url, headers=headers)
            if response.status_code in [200, 204]:
                print(f"✅ Deleted existing document (ID: {document_id})")
                return True
            else:
                print(f"⚠️ Failed to delete document: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ Error deleting document: {e}")
            return False

    def import_crawl_results(self, crawl_dir):
        """Import all markdown files from crawl results directory"""
        crawl_path = Path(crawl_dir)

        if not crawl_path.exists():
            print(f"❌ Crawl directory not found: {crawl_dir}")
            return

        # Find all markdown files (excluding duplicates folder)
        md_files = []
        for md_file in crawl_path.glob("*.md"):
            # Skip files that are in the duplicates folder or its subfolders
            if "duplicates" not in md_file.parts:
                md_files.append(md_file)

        if not md_files:
            print(f"❌ No markdown files found in {crawl_dir}")
            return

        # Check if duplicates folder exists and report
        duplicates_dir = crawl_path / "duplicates"
        if duplicates_dir.exists():
            duplicate_files = list(duplicates_dir.rglob("*.md"))
            print(f"📁 Found {len(duplicate_files)} duplicate files in duplicates/ folder (will be ignored)")
            print(f"📄 Processing {len(md_files)} unique content files")

        print(f"🚀 Found {len(md_files)} markdown files to import")

        successful_imports = []
        failed_imports = []

        # Pre-load existing documents cache for faster lookups
        if SKIP_EXISTING:
            self._load_existing_documents_cache()

        for md_file in md_files:
            # Skip report files
            if md_file.name in ['failed_urls.txt', 'crawl_summary.txt']:
                continue

            document_id = self.import_document_with_metadata(md_file)

            if document_id:
                successful_imports.append(str(md_file))
                # Small delay only for actual imports
                time.sleep(0.5)
            else:
                failed_imports.append(str(md_file))
                # Very short delay for failed/skipped documents
                time.sleep(0.1)

        # Summary
        print(f"\n📊 Import Summary:")
        print(f"✅ Successful: {len(successful_imports)}")
        print(f"❌ Failed: {len(failed_imports)}")

        if failed_imports:
            print(f"\n❌ Failed imports:")
            for failed in failed_imports:
                print(f"  - {failed}")

def main():
    """Main function"""
    if not DIFY_API_KEY:
        print("❌ Error: DIFY_API_KEY not set in .env file")
        return

    print("🚀 Starting Dify Metadata Importer")

    # Check if we need to create a new knowledge base
    dataset_id = DIFY_DATASET_ID
    if not dataset_id or dataset_id.strip() == "":
        print("📋 No dataset ID provided, creating new knowledge base...")

        # Create temporary importer to create knowledge base
        temp_importer = DifyMetadataImporter(DIFY_API_KEY, "", DIFY_BASE_URL)
        dataset_id = temp_importer.create_knowledge_base(
            name=DIFY_KNOWLEDGE_NAME,
            description=DIFY_KNOWLEDGE_DESCRIPTION,
            embedding_model=DIFY_EMBEDDING_MODEL,
            embedding_model_provider=DIFY_EMBEDDING_MODEL_PROVIDER,
            indexing_technique=DIFY_INDEXING_TECHNIQUE,
            permission=DIFY_PERMISSION,
            search_method=DIFY_SEARCH_METHOD,
            top_k=DIFY_TOP_K,
            score_threshold_enabled=DIFY_SCORE_THRESHOLD_ENABLED,
            score_threshold=DIFY_SCORE_THRESHOLD,
            reranking_enabled=DIFY_RERANKING_ENABLED,
            weights=DIFY_WEIGHTS
        )

        if not dataset_id:
            print("❌ Failed to create knowledge base. Exiting.")
            return

        # Update retrieval model configuration with weights
        temp_importer.update_retrieval_model(
            dataset_id=dataset_id,
            search_method=DIFY_SEARCH_METHOD,
            top_k=DIFY_TOP_K,
            score_threshold_enabled=DIFY_SCORE_THRESHOLD_ENABLED,
            score_threshold=DIFY_SCORE_THRESHOLD,
            reranking_enabled=DIFY_RERANKING_ENABLED,
            weights=DIFY_WEIGHTS,
            embedding_model=DIFY_EMBEDDING_MODEL,
            embedding_model_provider=DIFY_EMBEDDING_MODEL_PROVIDER
        )

        print(f"💡 Tip: Add this to your .env file to reuse this knowledge base:")
        print(f"   DIFY_DATASET_ID={dataset_id}")
        print()

    print(f"Dataset ID: {dataset_id}")
    print(f"Crawl Directory: {CRAWL_RESULT_DIR}")
    print("-" * 50)

    # Initialize importer with the dataset ID
    importer = DifyMetadataImporter(DIFY_API_KEY, dataset_id, DIFY_BASE_URL)

    # Setup metadata fields
    importer.setup_metadata_fields()

    # Import crawl results
    importer.import_crawl_results(CRAWL_RESULT_DIR)

    print("\n✅ Import process completed!")

if __name__ == "__main__":
    main()
