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

# --- INITIALISATION FIREBASE SÉCURISÉE ---
if not firebase_admin._apps:
    try:
        # Récupération de la clé encodée dans les secrets Streamlit
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur d'authentification : {e}")

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key=GROQ_API_KEY)

# --- FONCTIONS SYSTÈME (JARVIS STYLE) ---
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

# --- CHARGEMENT DE LA MÉMOIRE & IDENTIFICATION ---
res = doc_ref.get()
memoire = res.to_dict() if res.exists else {"profil": {}, "projets": {}, "divers": {}}

# Identification prioritaire de Monsieur Sezer dès l'ouverture
user_identity = memoire.get("profil", {}).get("nom", "Monsieur Sezer")

# --- INTERFACE ÉPURÉE ---
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
    .stChatMessage { border-radius: 15px; border: 1px solid rgba(0, 212, 255, 0.2); }
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
    
    # 1. FILTRE LUX RENFORCÉ (TRIDATA)
    try:
        extraction_prompt = (
            f"Tu es l'archiviste de {user_identity}. Analyse : '{prompt}'. "
            "RÈGLES : 1. N'extrais que des faits durables (Identité, Projets, Préférences). "
            "2. Ignore les questions ou politesses. "
            "3. Si rien n'est crucial, réponds 'NON_ESSENTIEL'. "
            "4. Sinon, mets à jour et renvoie ce JSON : "
            f"{json.dumps(memoire)}"
        )
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Trieur de données JSON binaire."},
                      {"role": "user", "content": extraction_prompt}]
        ).choices[0].message.content

        if "NON_ESSENTIEL" not in check and "{" in check:
            start = check.find('{')
            end = check.rfind('}') + 1
            new_data = json.loads(check[start:end])
            if new_data != memoire:
                memoire = new_data
                doc_ref.set(memoire, merge=True)
    except:
        pass

    # 2. RECHERCHE WEB INVISIBLE
    decision_prompt = f"Besoin du web pour : '{prompt}' ? OUI/NON."
    try:
        search_needed = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "user", "content": decision_prompt}]
        ).choices[0].message.content
    except:
        search_needed = "NON"
    
    web_data = web_lookup(prompt) if "OUI" in search_needed.upper() else ""

    # 3. RÉPONSE DE DELTA (JARVIS MODE)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        sys_instr = (
            f"Tu es DELTA. Ton créateur est {user_identity}. "
            f"SITUATION : {sys_info['date']}, {sys_info['heure']} au {sys_info['adresse']}. "
            f"ARCHIVES : {json.dumps(memoire)}. WEB : {web_data}. "
            "DIRECTIVES : "
            "1. Ton de Jarvis : Distingué, dévoué, EXTRÊMEMENT CONCIS. "
            "2. Utilise les ARCHIVES pour personnaliser ta réponse. "
            "3. Pas de mention technique. "
            "4. Ne termine par le nom du créateur que si absent du début."
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
