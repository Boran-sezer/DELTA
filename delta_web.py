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

# --- INTERFACE ADAPTATIVE (DARK/LIGHT MODE) ---
st.set_page_config(page_title="DELTA", layout="wide")

st.markdown("""
    <style>
    /* Suppression des éléments inutiles */
    button { display: none; }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Titre Adaptatif */
    .title-delta { 
        font-family: 'Inter', sans-serif; 
        font-weight: 800; 
        font-size: clamp(2rem, 8vw, 3.5rem); 
        text-align: center; 
        letter-spacing: -2px;
        margin-top: -40px;
        padding: 20px 0;
    }

    /* Bulles de chat adaptatives */
    .stChatMessage {
        border-radius: 15px;
        margin-bottom: 10px;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }

    /* Ajustement Mobile */
    @media (max-width: 640px) {
        .stChatMessage { padding: 5px; }
        .title-delta { margin-top: -20px; }
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="title-delta">DELTA</h1>', unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- LOGIQUE ---
if prompt := st.chat_input("À votre écoute, Monsieur Sezer..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Mémoire (Llama 8B)
    if len(prompt.split()) > 2:
        try:
            m_prompt = f"Archives: {archives}. Message: {prompt}. Update JSON memory."
            check = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": "JSON manager. No prose."}, {"role": "user", "content": m_prompt}],
                response_format={"type": "json_object"}
            )
            archives = json.loads(check.choices[0].message.content)
            doc_ref.set({"archives": archives}, merge=True)
        except: pass

    # Réponse (Personnalité Jarvis - Llama 70B)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        mem_ctx = f"Contexte: {json.dumps(archives)}" if archives else ""
        
        system_instruction = (
            f"Tu es DELTA, une IA de type JARVIS. Créateur: Monsieur Sezer. {mem_ctx}. "
            "TON : Très poli, dévoué, élégant. "
            "Termine par 'Monsieur Sezer'."
        )

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_instruction}] + st.session_state.messages[-8:],
                temperature=0.5,
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
        except Exception:
            st.error("Mes excuses, Monsieur Sezer, mes systèmes rencontrent une perturbation.")

        st.session_state.messages.append({"role": "assistant", "content": full_res})
