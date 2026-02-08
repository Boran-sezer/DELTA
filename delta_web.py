import streamlit as st
from groq import Groq
from duckduckgo_search import DDGS
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
from datetime import datetime
import pytz

# --- CONFIGURATION API ---
GROQ_API_KEY = "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"

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key=GROQ_API_KEY)

# --- FONCTIONS SYSTÈME (JARVIS STYLE) ---
def web_lookup(query):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            return "\n".join([f"[{r['title']}]: {r['body']}" for r in results]) if results else ""
    except: return ""

def get_precise_context():
    tz = pytz.timezone('Europe/Paris')
    now = datetime.now(tz)
    return {
        "date": now.strftime("%A %d %B %Y"),
        "heure": now.strftime("%H:%M"),
        "adresse": "58 Av. Beauregard, 74960 Annecy, France"
    }

# --- CHARGEMENT DE LA MÉMOIRE ---
res = doc_ref.get()
memoire = res.to_dict() if res.exists else {"profil": {}, "projets": {}, "divers": {}}

# --- INTERFACE ÉPURÉE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("""
    <style>
    button {display:none;} 
    #MainMenu, footer, header {visibility:hidden;} 
    .title-delta {
        font-family:'Inter'; font-weight:800; 
        text-align:center; letter-spacing:-3px; margin-top:-60px;
        color: white;
    }
    .stChatMessage { border-radius: 15px; border: 1px solid rgba(128, 128, 128, 0.1); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="title-delta">DELTA</h1>', unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CYCLE DE TRAITEMENT ---
if prompt := st.chat_input("À votre service..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    sys_info = get_precise_context()
    
    # 1. TRI INTELLIGENT DE MÉMOIRE (FILTRE LUX)
    try:
        extraction_prompt = (
            f"Agis comme l'archiviste de Monsieur Sezer. Analyse : '{prompt}'. "
            f"Extrais uniquement les faits durables (identité, préférences, projets). "
            f"Ignore le reste. Archives actuelles : {json.dumps(memoire)}. "
            "Réponds par le JSON fusionné ou 'NON_ESSENTIEL'."
        )
        check = client.chat.completions
