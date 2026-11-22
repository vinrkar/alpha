# src/rag/verfiy_retrieval.py

from src.rag.vector_store import FinancialVectorStore

def run_retrieval_check() -> None:
    store = FinancialVectorStore()
    results = store.similarity_search(query="portfolio risk and AAPL holdings", top_k=3)

    print("\n--- RAG Retrieval Test Results ---")
    for idx, doc in enumerate(results, start=1):
        snippet = str(doc.get("content", ""))[:80]
        print(
            f"{idx}. ID: {doc.get('id')} | Content Snippet: "
            f"{snippet}... | Metadata: {doc.get('metadata')}"
        )

if __name__ == "__main__":
    run_retrieval_check()