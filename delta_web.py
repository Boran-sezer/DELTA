import streamlit as st
from groq import Groq
from duckduckgo_search import DDGS
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import re
from datetime import datetime
import pytz

# --- CONFIGURATION ---
GROQ_API_KEY = "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"

# --- FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur : {e}")

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key=GROQ_API_KEY)

# --- TOOLS ---
def web_lookup(query):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            return "\n".join([f"[{r['title']}]: {r['body']}" for r in results]) if results else ""
    except: return ""

def get_context():
    tz = pytz.timezone('Europe/Paris')
    now = datetime.now(tz)
    return {"date": now.strftime("%d/%m/%Y"), "heure": now.strftime("%H:%M")}

# --- INITIALISATION ---
res = doc_ref.get()
memoire = res.to_dict() if res.exists else {}
user_identity = memoire.get("nom", "Monsieur Sezer")

# --- UI ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<style>button {display:none;} #MainMenu, footer, header {visibility:hidden;} .title-delta {font-family:'Inter'; font-weight:800; text-align:center; color: #00d4ff;}</style>", unsafe_allow_html=True)
st.markdown('<h1 class="title-delta">DELTA</h1>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CORE ---
if prompt := st.chat_input("Ordre..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. ARCHIVAGE LUX (SOUPLY & SMART)
    try:
        extraction_prompt = (
            f"Tu es l'archiviste de {user_identity}. Analyse : '{prompt}'. "
            f"Mémoire actuelle : {json.dumps(memoire)}. "
            "Si le message contient une information capitale (âge, projet, préférence), "
            "renvoie le JSON complet mis à jour. Sinon, réponds 'RIEN'."
        )
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "user", "content": extraction_prompt}]
        ).choices[0].message.content

        if "RIEN" not in check:
            match = re.search(r'\{.*\}', check, re.DOTALL)
            if match:
                memoire = json.loads(match.group())
                doc_ref.set(memoire, merge=True)
    except: pass

    # 2. WEB
    web_data = web_lookup(prompt) if "recherche" in prompt.lower() else ""

    # 3. RÉPONSE
    with st.chat_message("assistant"):
        ctx = get_context()
        sys_instr = (
            f"Tu es DELTA. Créateur : {user_identity}. "
            f"Infos : {ctx['date']}, {ctx['heure']}. Mémoire : {json.dumps(memoire)}. "
            "Ton : Jarvis, dévoué, ultra-concis. Utilise la mémoire pour personnaliser."
        )
        
        full_res = ""
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-5:],
            stream=True
        )
        placeholder = st.empty()
        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        placeholder.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
