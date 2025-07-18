import os
from dotenv import load_dotenv
load_dotenv()

import base64
import whisper
import numpy as np
import google.generativeai as genai
from gtts import gTTS
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.embeddings import Embeddings
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.chains import RetrievalQA
from langchain.chains import RetrievalQAWithSourcesChain
from langchain_core.messages import HumanMessage
from langchain.schema import Document
import requests
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
import ssl

# --- API key setup ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set in environment variables.")

os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY

genai.configure(api_key=GEMINI_API_KEY)

# --- SSL workaround for requests ---
class UnsafeAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl._create_unverified_context()
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

session = requests.Session()
session.mount("https://", UnsafeAdapter())
requests.get = session.get

def crawl_site(base_url, max_depth=2, visited=None):
    if visited is None:
        visited = set()
    docs = []
    def crawl(url, depth):
        if depth > max_depth or url in visited:
            return
        visited.add(url)
        try:
            response = requests.get(url, verify=False, timeout=10)
            response.raise_for_status()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            if text:
                docs.append(Document(page_content=text, metadata={"source": url}))
            for link_tag in soup.find_all("a", href=True):
                href = link_tag['href']
                from urllib.parse import urljoin, urlparse
                full_url = urljoin(url, href)
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    crawl(full_url, depth + 1)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
    crawl(base_url, 0)
    return docs

def run_notebook1(input_mode, input_value, audio_path):
    # input_mode: 'pdf' or 'url'
    # input_value: path to PDF or URL string
    # audio_path: path to input.wav
    docs = []
    if input_mode == "pdf":
        loader = PyPDFLoader(input_value)
        docs.extend(loader.load())
    elif input_mode == "url":
        docs = crawl_site(input_value, max_depth=3)
    else:
        raise ValueError("Invalid input type. Use 'pdf' or 'url'.")
    if not docs:
        raise ValueError("No documents loaded.")
    splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=100)
    chunks = splitter.split_documents(docs)
    embedding = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectorstore = FAISS.from_documents(chunks, embedding)
    vectorstore.save_local("faiss_index")
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
    qa_chain = RetrievalQAWithSourcesChain.from_chain_type(
        llm=llm,
        retriever=vectorstore.as_retriever(search_kwargs={"k": 10}),
        chain_type="stuff",
        return_source_documents=True
    )
    # Transcribe audio
    model = whisper.load_model("medium")
    result = model.transcribe(audio_path)
    transcribed_text = result["text"]
    # Query
    result = qa_chain.invoke(transcribed_text)
    rag_answer = result["answer"]
    source_docs = result.get("source_documents", [])
    # Self-evaluation
    def should_fallback_to_llm(question, rag_answer):
        evaluator = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)
        prompt = f"""
        Question: {question}\n\nRAG Answer: {rag_answer}\n\nIs the above answer helpful, relevant, and sufficient to answer the question accurately?\nOnly reply with one word: Yes or No.\n"""
        try:
            judgment = evaluator.invoke(prompt).content.strip().lower()
            return judgment.startswith("n")
        except Exception as e:
            print("Evaluation failed:", e)
            return True
    if should_fallback_to_llm(transcribed_text, rag_answer):
        final_response = llm.invoke(transcribed_text).content
    else:
        final_response = rag_answer
    # Text-to-speech
    tts = gTTS(final_response)
    tts.save("assistant_reply.mp3")
    return {
        "transcribed_text": transcribed_text,
        "final_response": final_response,
        "sources": [doc.metadata.get("source", "Unknown source") for doc in source_docs],
        "audio_reply_path": "assistant_reply.mp3"
    }

if __name__ == "__main__":
    # Example usage:
    # run_notebook1('pdf', 'yourfile.pdf', 'input.wav')
    pass 