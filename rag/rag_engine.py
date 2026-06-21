import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from dotenv import load_dotenv

load_dotenv()
DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "documents")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
def charger_documents():
    """Lit tous les fichiers .pdf et .txt du dossier documents/ et retourne leur contenu brut."""
    documents = []
    for nom_fichier in os.listdir(DOCUMENTS_DIR):
        chemin = os.path.join(DOCUMENTS_DIR, nom_fichier)
        if nom_fichier.endswith(".pdf"):
            loader = PyPDFLoader(chemin)
        elif nom_fichier.endswith(".txt"):
            loader = TextLoader(chemin, encoding="utf-8")
        else:
            continue
        documents.extend(loader.load())
    return documents
def decouper_en_chunks(documents):
    """Découpe les documents en petits morceaux (chunks) pour pouvoir les indexer."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    return splitter.split_documents(documents)
def construire_base_vectorielle():
    """Pipeline complet : charge les documents, les découpe, calcule les embeddings, et les stocke dans ChromaDB."""
    documents = charger_documents()
    if not documents:
        raise ValueError("Aucun document trouvé dans rag/documents/. Ajoutez au moins un fichier .pdf ou .txt.")

    chunks = decouper_en_chunks(documents)

    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_DIR
    )
    return vectorstore
def charger_base_existante():
    """Recharge une base vectorielle déjà construite, sans tout recalculer."""
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    return Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
def rechercher_contexte(question, k=3):
    """Cherche les k passages les plus pertinents pour répondre à la question."""
    if os.path.exists(CHROMA_DIR) and os.listdir(CHROMA_DIR):
        vectorstore = charger_base_existante()
    else:
        vectorstore = construire_base_vectorielle()

    resultats = vectorstore.similarity_search(question, k=k)
    return "\n\n".join([doc.page_content for doc in resultats])
if __name__ == "__main__":
    print("Construction de la base vectorielle...")
    construire_base_vectorielle()
    print("Terminé ! Base stockée dans :", CHROMA_DIR)

    question_test = "Combien de jours de congés ai-je ?"
    print("\nTest de recherche pour :", question_test)
    print(rechercher_contexte(question_test))