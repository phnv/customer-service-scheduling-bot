import os
import glob
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# configuration
KNOWLEDGE_DIR = os.path.join(os.path.dirname(__file__), '..', 'knowledge')
VECTORSTORE_DIR = os.path.join(os.path.dirname(__file__), '..', 'vectorstore', 'chroma')

def main():
    print("Loading documents...")
    files = glob.glob(os.path.join(KNOWLEDGE_DIR, '**', '*.*'), recursive=True)
    
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ])
    
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    
    all_chunks = []
    
    for file_path in files:
        if not file_path.endswith('.md'):
            continue
            
        print(f"Processing {os.path.basename(file_path)}")
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Try markdown splitting first
        md_chunks = md_splitter.split_text(content)
        
        # We process each chunk with the character splitter
        for chunk in md_chunks:
            # Add file info to metadata
            chunk.metadata['source'] = os.path.basename(file_path)
            
            # Further split by characters if needed
            sub_chunks = char_splitter.split_documents([chunk])
            all_chunks.extend(sub_chunks)

    print(f"Total chunks created: {len(all_chunks)}")
    
    if not all_chunks:
        print("No content found to ingest.")
        return

    print("Initializing embedding model (all-MiniLM-L6-v2)...")
    # Langchain HuggingFaceEmbeddings uses sentence-transformers under the hood
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    print(f"Storing in ChromaDB at {VECTORSTORE_DIR}...")
    vectorstore = Chroma.from_documents(
        documents=all_chunks,
        embedding=embeddings,
        persist_directory=VECTORSTORE_DIR
    )
    
    print("Ingestion complete!")

if __name__ == "__main__":
    main()
