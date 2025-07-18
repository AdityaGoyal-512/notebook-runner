import os
from dotenv import load_dotenv
load_dotenv()

import ssl
import uuid
import time
import base64
import requests
from pydub import AudioSegment
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.schema import Document
from langchain_community.document_loaders import PyPDFLoader
from langchain.chains import RetrievalQAWithSourcesChain
import subprocess

# --- API Keys from environment ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not set in environment variables.")
if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN or not TWILIO_PHONE_NUMBER:
    raise ValueError("Twilio credentials not set in environment variables.")
if not GOOGLE_APPLICATION_CREDENTIALS:
    raise ValueError("GOOGLE_APPLICATION_CREDENTIALS not set in environment variables.")

os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)

from google.cloud import speech, texttospeech
speech_client = speech.SpeechClient()
tts_client = texttospeech.TextToSpeechClient()

# --- SSL workaround for requests ---
class UnsafeAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = ssl._create_unverified_context()
        kwargs['ssl_context'] = context
        return super().init_poolmanager(*args, **kwargs)

session = requests.Session()
session.mount("https://", UnsafeAdapter())
requests.get = session.get

def crawl_site(base_url, max_depth=3, visited=None):
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
            soup = BeautifulSoup(response.text, "html.parser")
            text = soup.get_text(separator=" ", strip=True)
            if text:
                docs.append(Document(page_content=text, metadata={"source": url}))
            for link_tag in soup.find_all("a", href=True):
                href = link_tag['href']
                full_url = urljoin(url, href)
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    crawl(full_url, depth + 1)
        except Exception as e:
            print(f"Failed to fetch {url}: {e}")
    crawl(base_url, 0)
    return docs

def transcribe_audio_google(audio_path):
    wav_path = audio_path.replace(".mp3", ".wav")
    ffmpeg_command = [
        "ffmpeg",
        "-i", audio_path,
        "-acodec", "pcm_s16le",
        "-ac", "1",
        "-ar", "16000",
        wav_path
    ]
    try:
        subprocess.run(ffmpeg_command, check=True, capture_output=True)
    except Exception as e:
        print(f"FFmpeg conversion failed: {e}")
        raise
    try:
        with open(wav_path, "rb") as audio_file:
            content = audio_file.read()
        audio_config = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        response = speech_client.recognize(config=config, audio=audio_config)
        transcript = " ".join([result_alt.alternatives[0].transcript for result_alt in response.results])
        return transcript.strip()
    except Exception as e:
        print(f"Google Speech-to-Text API call failed: {e}")
        return ""

def synthesize_speech_google(text, output_path):
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = tts_client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    with open(output_path, "wb") as out:
        out.write(response.audio_content)

def run_notebook2(input_mode, input_value, audio_path):
    # input_mode: 'pdf' or 'url'
    # input_value: path to PDF or URL string
    # audio_path: path to input.mp3
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
    retriever = vectorstore.as_retriever(search_kwargs={"k": 10})
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
    qa_chain = RetrievalQAWithSourcesChain.from_chain_type(
        llm=llm,
        retriever=retriever,
        chain_type="stuff",
        return_source_documents=True
    )
    transcribed_text = transcribe_audio_google(audio_path)
    if not transcribed_text:
        return {"error": "Empty transcription."}
    fixer = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
    clarification_prompt = f"""
    You are an assistant helping clean up possibly imperfect speech-to-text transcription.
    This was transcribed from audio: "{transcribed_text}"
    Fix transcription errors, clean up names, and clarify what's being asked so it aligns with known content in a knowledge base.
    Output a single improved version of the user's intended query:
    """
    try:
        rephrased_query = fixer.invoke(clarification_prompt).content.strip()
    except Exception as e:
        print(f"Failed to rephrase query: {e}")
        rephrased_query = transcribed_text
    result = qa_chain(rephrased_query)
    rag_answer = result["answer"]
    sources = result.get("source_documents", [])
    def should_fallback_to_llm(question, rag_answer):
        evaluator = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)
        prompt = f"""
        Question: {question}\nRAG Answer: {rag_answer}\nIs the above answer helpful, relevant, and sufficient to answer the question accurately?\nOnly reply with one word: Yes or No.\n"""
        try:
            judgment = evaluator.invoke(prompt).content.strip().lower()
            return judgment.startswith("n")
        except:
            return True
    if should_fallback_to_llm(rephrased_query, rag_answer):
        final_response = fixer.invoke(rephrased_query).content.strip()
    else:
        final_response = rag_answer
    reply_path = "assistant_reply.mp3"
    synthesize_speech_google(final_response, reply_path)
    return {
        "transcribed_text": transcribed_text,
        "final_response": final_response,
        "sources": [doc.metadata.get("source", "Unknown source") for doc in sources],
        "audio_reply_path": reply_path
    }

if __name__ == "__main__":
    # Example usage:
    # run_notebook2('pdf', 'yourfile.pdf', 'input.mp3')
    pass 