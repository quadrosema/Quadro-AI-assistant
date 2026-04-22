"""
Memory with lazy loading to avoid blocking startup.
"""

import sqlite3
import os
from colorama import Fore

DB_PATH = "data/jarvis_memory.db"
CHROMA_PATH = "data/chroma"

class Memory:
    def __init__(self):
        # Don't import heavy libraries yet
        self.chroma_collection = None
        self.embedding_model = None
        self._initialized = False
        
        # Only create SQLite connection (lightweight)
        os.makedirs("data", exist_ok=True)
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._init_db()
        
        print(Fore.GREEN + "   ✅ Memory Online (lazy load)")
    
    def _init_db(self):
        """Create tables if they don't exist."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()
    
    def _ensure_initialized(self):
        """Lazy load heavy dependencies."""
        if self._initialized:
            return
        
        print(Fore.YELLOW + "   (Loading embedding model...)")
        
        # Import here to defer loading
        import chromadb
        from sentence_transformers import SentenceTransformer
        
        # Load embedding model
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        
        # Init ChromaDB
        chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        self.chroma_collection = chroma_client.get_or_create_collection(
            name="jarvis_facts",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Sync existing facts
        self._sync_chroma()
        self._initialized = True
        
        count = self.conn.cursor().execute("SELECT COUNT(*) FROM facts").fetchone()[0]
        print(Fore.GREEN + f"   ✅ Memory Initialized ({count} facts indexed)")
    
    def _sync_chroma(self):
        """Sync SQLite facts to ChromaDB."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id, fact FROM facts")
        facts = cursor.fetchall()
        
        if not facts:
            return
        
        existing_ids = set(self.chroma_collection.get()['ids'])
        
        for fact_id, fact in facts:
            str_id = str(fact_id)
            if str_id not in existing_ids:
                embedding = self.embedding_model.encode(fact).tolist()
                self.chroma_collection.add(
                    ids=[str_id],
                    documents=[fact],
                    embeddings=[embedding]
                )
    
    def save_fact(self, fact):
        """Save a fact to memory."""
        self._ensure_initialized()
        
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO facts (fact) VALUES (?)", (fact,))
        self.conn.commit()
        fact_id = cursor.lastrowid
        
        # Add to ChromaDB
        embedding = self.embedding_model.encode(fact).tolist()
        self.chroma_collection.add(
            ids=[str(fact_id)],
            documents=[fact],
            embeddings=[embedding]
        )
        
        return f"Got it. I'll remember that."
    
    def get_relevant_facts(self, query, top_k=3):
        """Retrieve relevant facts using semantic search."""
        self._ensure_initialized()
        
        if not query:
            return ""
        
        query_embedding = self.embedding_model.encode(query).tolist()
        results = self.chroma_collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        
        if not results['documents'] or not results['documents'][0]:
            return ""
        
        facts = []
        for doc, distance in zip(results['documents'][0], results['distances'][0]):
            if distance < 0.7:
                facts.append(f"- {doc}")
        
        return "\n".join(facts) if facts else ""
    
    def wipe_facts(self):
        """Delete all facts."""
        self._ensure_initialized()
        
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM facts")
        self.conn.commit()
        
        # Clear ChromaDB
        all_ids = self.chroma_collection.get()['ids']
        if all_ids:
            self.chroma_collection.delete(ids=all_ids)
        
        return "All memories wiped. Starting fresh."