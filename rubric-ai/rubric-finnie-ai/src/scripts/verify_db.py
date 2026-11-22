# src/utils/check_db.py

import argparse
import os

import chromadb
from dotenv import load_dotenv

load_dotenv()

def main() -> None:
    if not os.getenv("API_KEY"):
        print("⚠️ Warning: API_KEY is not set in the environment or .env file.")

    parser = argparse.ArgumentParser(description="Inspect ChromaDB local volume data.")
    parser.add_argument(
        "query",
        nargs="?",
        default="Apple",
        help="Search string or company name to query (default: 'Apple')",
    )
    parser.add_argument(
        "--path",
        default="./data/chroma_db",
        help="Path to ChromaDB persistent storage volume (default: './data/chroma_db')",
    )
    args = parser.parse_args()

    print(f"🔌 Connecting to local ChromaDB volume at: {args.path}")
    client = chromadb.PersistentClient(path=args.path)

    collections = client.list_collections()
    print(f"📦 Collections found: {[col.name for col in collections]}\n")

    if not collections:
        print("⚠️ No collections found in this volume path. Run ingestion first.")
        return

    for col_info in collections:
        col = client.get_collection(col_info.name)
        print(f"📁 Collection '{col_info.name}' contains {col.count()} total documents/chunks.")
        print(f"\n🔍 Searching for query: '{args.query}' in '{col_info.name}'...")

        results = col.query(query_texts=[args.query], n_results=3)
        docs = (results.get("documents") or [[]])[0]
        metas = (results.get("metadatas") or [[]])[0]
        ids = (results.get("ids") or [[]])[0]

        if docs:
            for doc_text, meta, doc_id in zip(docs, metas, ids):
                print(f" -> ID: {doc_id} | Meta: {meta}\n    Text: {doc_text[:120]}...\n")
        else:
            print(f" ⚠️ No matching documents found for '{args.query}'.\n")

if __name__ == "__main__":
    main()