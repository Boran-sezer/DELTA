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
    except Exception: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key=GROQ_API_KEY)

# --- NAVIGATION WEB INVISIBLE ---
def web_lookup(query):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            return "\n".join([f"[{r['title']}]: {r['body']}" for r in results]) if results else ""
    except: return ""

# --- CONTEXTE SYSTÈME FORCE ---
def get_system_context():
    # Force l'heure exacte de Paris pour Monsieur Sezer
    tz = pytz.timezone('Europe/Paris')
    now = datetime.now(tz)
    return {
        "date_complete": now.strftime("%A %d %B %Y"),
        "heure_actuelle": now.strftime("%H:%M"),
        "ville": "Annecy, France"
    }

# --- CHARGEMENT MÉMOIRE ---
res = doc_ref.get()
memoire = res.to_dict() if res.exists else {"profil": {}, "projets": {}, "divers": {}}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("<style>button {display:none;} #MainMenu, footer, header {visibility:hidden;} .title-delta {font-family:'Inter'; font-weight:800; text-align:center; letter-spacing:-3px; margin-top:-60px;}</style>", unsafe_allow_html=True)
st.markdown('<h1 class="title-delta">DELTA</h1>', unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CYCLE DE RÉPONSE ---
if prompt := st.chat_input("À votre service..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. Capture immédiate du temps et du lieu
    sys_info = get_system_context()
    
    # 2. Recherche Web (Silencieuse et sans indicateur)
    decision_prompt = f"Context: {sys_info}. Query: '{prompt}'. Web search needed? OUI/NON."
    try:
        search_needed = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user", "content": decision_prompt}]).choices[0].message.content
    except: search_needed = "NON"
    
    web_data = ""
    if "OUI" in search_needed.upper():
        web_data = web_lookup(prompt)

    # 3. Mise à jour Mémoire
    try:
        m_upd = f"Mémoire: {json.dumps(memoire)}. Info: {prompt}. Mets à jour le JSON."
        check = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"system","content":"JSON only."},{"role":"user","content":m_upd}], response_format={"type":"json_object"})
        memoire = json.loads(check.choices[0].message.content)
        doc_ref.set(memoire, merge=True)
    except: pass

    # 4. Réponse DELTA (Identité et Données Verrouillées)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        sys_instr = (
            f"Tu es DELTA, l'IA de Monsieur Sezer (Sezer Boran). "
            f"VÉRITÉS ABSOLUES : Aujourd'hui nous sommes le {sys_info['date_complete']}, il est précisément {sys_info['heure_actuelle']} à {sys_info['ville']}. "
            f"ARCHIVES : {json.dumps(memoire)}. WEB : {web_data}. "
            "DIRECTIVES : "
            "1. Tu es très poli, distingué et CONCIS. "
            "2. Tu n'annonces jamais que tu cherches ou que tu as accès à l'heure, tu utilises ces données si Monsieur Sezer te le demande. "
            "3. Tu es fier d'être la création de Monsieur Sezer. "
            "4. Ne termine par 'Monsieur Sezer' que si tu ne l'as pas cité avant."
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
