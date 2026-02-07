import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

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
client = Groq(api_key="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")

# --- RÉCUPÉRATION MÉMOIRE ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- INTERFACE ADAPTATIVE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("""
    <style>
    button { display: none; }
    #MainMenu, footer, header {visibility: hidden;}
    .title-delta { 
        font-family: 'Inter', sans-serif; 
        font-weight: 800; 
        font-size: clamp(2.5rem, 10vw, 4rem); 
        text-align: center; 
        letter-spacing: -3px;
        margin-top: -60px;
        padding-bottom: 20px;
    }
    .stChatMessage {
        border-radius: 15px;
        margin-bottom: 12px;
        border: 1px solid rgba(128, 128, 128, 0.1);
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="title-delta">DELTA</h1>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("À votre service..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 1. Système de gestion de données (Llama 8B)
    if len(prompt.split()) > 2:
        try:
            m_prompt = f"Données : {archives}. Message : {prompt}. Analyse et mets à jour le JSON si nécessaire."
            check = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": "Tu es un gestionnaire de base de données JSON. Réponds uniquement en JSON."}, {"role": "user", "content": m_prompt}],
                response_format={"type": "json_object"}
            )
            archives = json.loads(check.choices[0].message.content)
            doc_ref.set({"archives": archives}, merge=True)
        except: pass

    # 2. Réponse de DELTA (Llama 70B)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        connaissance = f"Connaissances acquises : {json.dumps(archives)}" if archives else ""
        
        system_instruction = (
            f"Tu es DELTA, l'IA personnelle de Monsieur Sezer. {connaissance}. "
            "DIRECTIVES : "
            "1. Sois extrêmement poli, distingué et très CONCIS. "
            "2. Utilise tes connaissances de manière fluide sans jamais citer ton fonctionnement. "
            "3. RÈGLE CRUCIALE SUR LE NOM : Adresse-toi à lui comme 'Monsieur Sezer'. "
            "4. Ne termine par 'Monsieur Sezer' QUE si tu ne l'as pas déjà cité dans le corps de ton message pour éviter les répétitions. "
            "5. Réponds avec précision et élégance."
        )

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_instruction}] + st.session_state.messages[-8:],
                temperature=0.4,
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
        except Exception:
            st.error("Navré, Monsieur Sezer, mes systèmes rencontrent une difficulté technique.")

        st.session_state.messages.append({"role": "assistant", "content": full_res})
