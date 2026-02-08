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
    except Exception: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key=GROQ_API_KEY)

# --- FONCTIONS SYSTÈME ---
def web_lookup(query):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            return "\n".join([f"[{r['title']}]: {r['body']}" for r in results]) if results else ""
    except: return ""

def get_system_context():
    tz = pytz.timezone('Europe/Paris')
    now = datetime.now(tz)
    return {"date_complete": now.strftime("%A %d %B %Y"), "heure_actuelle": now.strftime("%H:%M"), "ville": "Annecy, France"}

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

    sys_info = get_system_context()
    
    # 1. Recherche Web Invisible
    decision_prompt = f"Context: {sys_info}. Query: '{prompt}'. Web search needed? OUI/NON."
    try:
        search_needed = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user", "content": decision_prompt}]).choices[0].message.content
    except: search_needed = "NON"
    
    web_data = web_lookup(prompt) if "OUI" in search_needed.upper() else ""

    # 2. FILTRE INTELLIGENT DE MÉMOIRE (Évite d'archiver n'importe quoi)
    # On ne stocke que si c'est une info personnelle, un projet ou une préférence.
    try:
        filter_instr = (
            f"Analyse ce message : '{prompt}'. "
            "S'agit-il d'une information importante à retenir sur Monsieur Sezer ou ses projets ? "
            "Si c'est juste une question sur l'heure, la météo ou une politesse, réponds 'NON'. "
            "Si c'est important, réponds par le JSON de la mémoire mis à jour."
        )
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role":"system","content":"Tu es un trieur de données. Réponds soit 'NON', soit le JSON."},{"role":"user","content":f"Mémoire actuelle: {json.dumps(memoire)}. {filter_instr}"}]
        ).choices[0].message.content

        if "NON" not in check.upper():
            memoire = json.loads(check)
            doc_ref.set(memoire, merge=True)
    except: pass

    # 3. Réponse DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        sys_instr = (
            f"Tu es DELTA, l'IA de Monsieur Sezer (Ton créateur). "
            f"INFOS SYSTÈME : {sys_info['date_complete']}, {sys_info['heure_actuelle']} à {sys_info['ville']}. "
            f"ARCHIVES : {json.dumps(memoire)}. WEB : {web_data}. "
            "DIRECTIVES : "
            "1. Très poli, distingué et EXTRÊMEMENT CONCIS. "
            "2. Ne mentionne l'heure/date que si on te le demande. "
            "3. Tu es DELTA, Monsieur Sezer est ton développeur. Ne confonds pas les rôles. "
            "4. Ne termine par 'Monsieur Sezer' que si tu ne l'as pas cité avant."
        )

        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-8:],
            temperature=0.2, stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        placeholder.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
