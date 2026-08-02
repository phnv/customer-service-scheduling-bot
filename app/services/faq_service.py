import os
import logging
from sqlmodel import Session, select
from app.database.engine import engine
from app.database.models import Service, Doctor

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

    def search_services(
        self,
        specialty: str | None = None,
        service_type: str | None = None,
        service_mode: str | None = None,
    ) -> list[dict]:
        """
        Searches the database for available services.
        Joins with the Doctor table to return doctor names.
        """
        logger.info(f"[FAQService] Searching services: specialty={specialty}, type={service_type}, mode={service_mode}")
        
        with Session(engine) as session:
            statement = select(Service, Doctor).join(Doctor, Service.doctor_id == Doctor.doctor_id).where(Service.is_active == True)
            
            if specialty:
                statement = statement.where(Service.specialty.ilike(f"%{specialty}%"))
            if service_type:
                statement = statement.where(Service.service_type == service_type)
            if service_mode:
                statement = statement.where(Service.service_mode == service_mode)
                
            results = session.exec(statement).all()
            
            formatted_results = []
            for service, doctor in results:
                s_type = service.service_type.value if hasattr(service.service_type, 'value') else service.service_type
                s_mode = service.service_mode.value if hasattr(service.service_mode, 'value') else service.service_mode
                formatted_results.append({
                    "service_id": service.service_id,
                    "doctor_name": doctor.full_name,
                    "specialty": service.specialty,
                    "service_type": s_type,
                    "service_mode": s_mode,
                    "price": service.price
                })
                
            return formatted_results
