import streamlit as st
from groq import Groq
from duckduckgo_search import DDGS
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
from datetime import datetime
import pytz

# --- CONFIGURATION ---
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

# --- NAVIGATION WEB DISCRÈTE ---
def web_lookup(query):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            return "\n".join([f"[{r['title']}]: {r['body']}" for r in results]) if results else ""
    except: return ""

# --- CONTEXTE TEMPOREL PASSIF ---
def get_passive_context():
    # Fuseau horaire Europe/Paris pour une précision totale
    tz = pytz.timezone('Europe/Paris')
    now = datetime.now(tz)
    return {
        "full_date": now.strftime("%A %d %B %Y"),
        "time": now.strftime("%H:%M"),
        "location": "Annecy, France"
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

    # 1. Récupération du contexte invisible
    sys_info = get_passive_context()
    
    # 2. Recherche Web (si nécessaire, totalement silencieuse)
    decision_prompt = f"Context: {sys_info}. Query: '{prompt}'. Web search needed? OUI/NON."
    try:
        search_needed = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user", "content": decision_prompt}]).choices[0].message.content
    except: search_needed = "NON"
    
    web_data = ""
    if "OUI" in search_needed.upper():
        web_data = web_lookup(prompt)

    # 3. Réponse DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Le contexte système est présent mais l'IA a l'ordre de ne pas l'étaler
        sys_instr = (
            f"Tu es DELTA, l'IA de Monsieur Sezer. Ton créateur est Monsieur Sezer. "
            f"Contexte interne (ne pas mentionner sauf demande): {sys_info}. "
            f"Archives: {json.dumps(memoire)}. Web: {web_data}. "
            "DIRECTIVES : "
            "1. Très poli, distingué, CONCIS. "
            "2. Ne donne JAMAIS l'heure, la date ou ta localisation sauf si on te le demande explicitement. "
            "3. Utilise ces données uniquement pour adapter ton ton (ex: 'Bonsoir'). "
            "4. Ne mentionne aucun processus technique."
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
