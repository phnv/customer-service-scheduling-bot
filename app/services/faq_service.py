import os
import logging
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

logger = logging.getLogger(__name__)

VECTORSTORE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'vectorstore', 'chroma'))

class FAQService:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        self.vectorstore = Chroma(
            persist_directory=VECTORSTORE_DIR,
            embedding_function=self.embeddings
        )

    def search_knowledge_base(self, query: str, top_k: int = 3) -> list[dict]:
        """
        Searches the vector store for the query and returns the top_k results.
        """
        logger.info(f"[FAQService] Searching knowledge base for: {query!r}")
        
        # similarity_search_with_score returns a list of (Document, float) where the float is L2 distance
        results = self.vectorstore.similarity_search_with_score(query, k=top_k)
        
        formatted_results = []
        for doc, score in results:
            title_parts = []
            for header_level in ["Header 1", "Header 2", "Header 3"]:
                if header_level in doc.metadata:
                    title_parts.append(doc.metadata[header_level])
            
            # fallback to source file if no markdown headers
            if not title_parts and "source" in doc.metadata:
                title_parts.append(doc.metadata["source"])
            
            title = " > ".join(title_parts) if title_parts else "Unknown Section"
            
            formatted_results.append({
                "title": title,
                "content": doc.page_content,
                "score": float(score)
            })
            
        return formatted_results
