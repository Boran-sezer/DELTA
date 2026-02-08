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

# --- CONFIGURATION API ---
GROQ_API_KEY = "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"

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur d'accès Firebase : {e}")

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key=GROQ_API_KEY)

# --- FONCTIONS SYSTÈME ---
def web_lookup(query):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            return "\n".join([f"[{r['title']}]: {r['body']}" for r in results]) if results else ""
    except:
        return ""

def get_precise_context():
    tz = pytz.timezone('Europe/Paris')
    now = datetime.now(tz)
    return {
        "date": now.strftime("%A %d %B %Y"),
        "heure": now.strftime("%H:%M"),
        "adresse": "58 Av. Beauregard, 74960 Annecy, France"
    }

# --- CHARGEMENT INITIAL ---
res = doc_ref.get()
memoire = res.to_dict() if res.exists else {"profil": {}, "projets": {}, "divers": {}}
user_identity = memoire.get("profil", {}).get("nom", "Monsieur Sezer")

# --- INTERFACE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("""
    <style>
    button {display:none;} 
    #MainMenu, footer, header {visibility:hidden;} 
    .title-delta {
        font-family:'Inter'; font-weight:800; 
        text-align:center; letter-spacing:-3px; margin-top:-60px;
        color: #00d4ff;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="title-delta">DELTA</h1>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- CYCLE DE TRAITEMENT ---
if prompt := st.chat_input("À votre service..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    sys_info = get_precise_context()
    
   # 1. ARCHIVAGE AVEC TRI STRUCTURÉ (FILTRE LUX ÉVOLUÉ)
    try:
        extraction_prompt = (
            f"Analyse ce message : '{prompt}'. "
            "Tu dois classer les nouvelles informations dans ce JSON structuré : "
            "{'profil': {'nom': '', 'age': '', 'preferences': []}, 'projets': {}, 'divers': {}}. "
            f"Voici la mémoire actuelle : {json.dumps(memoire)}. "
            "RÈGLES : "
            "1. Si l'info concerne l'identité (âge, nom), mets-la dans 'profil'. "
            "2. Si c'est un travail ou une idée, mets-la dans 'projets'. "
            "3. Si aucune info durable n'est présente, réponds STRICTEMENT : AUCUN_CHANGEMENT. "
            "4. Renvoie le JSON COMPLET mis à jour."
        )
        
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Tu es un expert en structuration de données JSON."},
                      {"role": "user", "content": extraction_prompt}]
        ).choices[0].message.content

        if "AUCUN_CHANGEMENT" not in check:
            match = re.search(r'\{.*\}', check, re.DOTALL)
            if match:
                new_data = json.loads(match.group())
                # On s'assure que la structure est respectée avant de sauvegarder
                if any(key in new_data for key in ['profil', 'projets', 'divers']):
                    memoire = new_data
                    doc_ref.set(memoire, merge=True)
    except:
        pass
    # 2. RECHERCHE WEB
    decision_prompt = f"Besoin du web pour : '{prompt}' ? OUI/NON."
    try:
        search_needed = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "user", "content": decision_prompt}]
        ).choices[0].message.content
    except:
        search_needed = "NON"
    
    web_data = web_lookup(prompt) if "OUI" in search_needed.upper() else ""

    # 3. RÉPONSE DE DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        sys_instr = (
            f"Tu es DELTA. Ton créateur est {user_identity}. "
            f"CONTEXTE : {sys_info['date']}, {sys_info['heure']} à {sys_info['adresse']}. "
            f"MÉMOIRE : {json.dumps(memoire)}. WEB : {web_data}. "
            "DIRECTIVES : "
            "1. Ton de Jarvis : Distingué, dévoué, TRÈS CONCIS. "
            "2. Utilise la MÉMOIRE pour personnaliser. "
            "3. Ne mentionne ta position que si demandé. "
            "4. Finis par le nom de l'utilisateur uniquement si tu ne l'as pas dit au début."
        )

        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-8:],
            temperature=0.3, stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        placeholder.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
