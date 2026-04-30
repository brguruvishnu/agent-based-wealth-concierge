"""
setup_memory.py — Run once to seed ChromaDB with user's long-term financial goals.
Uses SentenceTransformer embeddings for semantic search by the Execution Agent.
"""

import os
import sys

# Force UTF-8 output on Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMORY_PATH = os.path.join(BASE_DIR, "wealth_memory")

goals = [
    "I want to maintain an emergency fund of 2,00,000 INR at all times.",
    "I want to invest 20% of my monthly income into Nifty 50 index funds.",
    "My risk tolerance is aggressive because I am a young student with no dependents.",
]

GOAL_IDS = ["goal_1", "goal_2", "goal_3"]


def setup_memory() -> None:
    """Initialise ChromaDB and seed user goals if not already present."""
    print("🧠 Setting up ChromaDB memory store...")

    os.makedirs(MEMORY_PATH, exist_ok=True)

    embedding_fn = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path=MEMORY_PATH)

    collection = client.get_or_create_collection(
        name="user_goals",
        embedding_function=embedding_fn,
    )

    # Idempotency: only add goals whose IDs are not already present
    existing = collection.get()
    existing_ids = set(existing["ids"])

    goals_to_add = [
        (gid, goal)
        for gid, goal in zip(GOAL_IDS, goals)
        if gid not in existing_ids
    ]

    if not goals_to_add:
        print("✅ Memory already seeded. No duplicates added.")
    else:
        ids, documents = zip(*goals_to_add)
        collection.add(ids=list(ids), documents=list(documents))
        print(f"✅ Added {len(goals_to_add)} goal(s) to memory:")
        for gid, goal in goals_to_add:
            print(f"   [{gid}] {goal}")

    print(f"\n📦 Collection now has {collection.count()} goal(s) stored.")
    print(f"💾 Memory path: {MEMORY_PATH}")


if __name__ == "__main__":
    setup_memory()
