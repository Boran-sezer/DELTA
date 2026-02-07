import streamlit as st
from groq import Groq
from duckduckgo_search import DDGS
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

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

# --- FONCTION RECHERCHE WEB SILENCIEUSE ---
def web_lookup(query):
    try:
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(query, max_results=3)]
            return "\n".join([f"[{r['title']}]: {r['body']}" for r in results]) if results else ""
    except: return ""

# --- CHARGEMENT DE LA MÉMOIRE ---
res = doc_ref.get()
memoire = res.to_dict() if res.exists else {"profil": {}, "projets": {}, "divers": {}}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("""
    <style>
    button {display:none;} 
    #MainMenu, footer, header {visibility:hidden;} 
    .title-delta {
        font-family:'Inter'; font-weight:800; 
        font-size:clamp(2.5rem, 10vw, 4rem); 
        text-align:center; letter-spacing:-3px; margin-top:-60px;
    }
    .stChatMessage { border-radius: 15px; margin-bottom: 12px; border: 1px solid rgba(128, 128, 128, 0.1); }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="title-delta">DELTA</h1>', unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- TRAITEMENT ---
if prompt := st.chat_input("À votre service..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. Analyse et Recherche Web invisible
    decision_prompt = f"L'utilisateur demande : '{prompt}'. Faut-il faire une recherche web ? Répondre par OUI ou NON."
    try:
        search_needed = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role":"user", "content": decision_prompt}]
        ).choices[0].message.content
    except: search_needed = "NON"
    
    web_data = ""
    if "OUI" in search_needed.upper():
        # Exécution en arrière-plan sans affichage Streamlit
        web_data = web_lookup(prompt)

    # 2. Mise à jour Mémoire Silencieuse
    try:
        m_upd = f"Mémoire: {json.dumps(memoire)}. Info: {prompt}. Mets à jour le JSON."
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role":"system","content":"JSON only."},{"role":"user","content":m_upd}], 
            response_format={"type":"json_object"}
        )
        memoire = json.loads(check.choices[0].message.content)
        doc_ref.set(memoire, merge=True)
    except: pass

    # 3. Réponse de DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        context = f"Identité créateur : Monsieur Sezer. Connaissances : {json.dumps(memoire)}. Web : {web_data}."
        
        sys_instr = (
            f"Tu es DELTA, l'IA de Monsieur Sezer. {context}. "
            "1. Très poli, distingué, CONCIS. "
            "2. Ne mentionne jamais que tu fais une recherche ou que tu accèdes à des données. "
            "3. Utilise les informations du web naturellement comme si elles faisaient partie de tes propres connaissances. "
            "4. Ne termine par 'Monsieur Sezer' que si tu ne l'as pas cité avant."
        )

        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-8:],
            temperature=0.4, stream=True
        )
        for chunk in stream:
            if chunk.choices[0].delta.content:
                full_res += chunk.choices[0].delta.content
                placeholder.markdown(full_res + "▌")
        placeholder.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
