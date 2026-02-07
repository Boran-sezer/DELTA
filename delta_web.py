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
    except Exception as e:
        st.error(f"Erreur Firebase: {e}")

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")

# --- AUTHENTIFICATION GROQ ---
client = Groq(api_key="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")

# --- RÉCUPÉRATION MÉMOIRE STABLE ---
def get_memory():
    try:
        res = doc_ref.get()
        return res.to_dict().get("archives", {}) if res.exists else {}
    except:
        return {}

archives = get_memory()

# --- INTERFACE SOBRE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("""
    <style>
    .stApp { background: #ffffff; color: #1a1a1a; }
    .stChatMessage { background-color: #f7f7f8; border-radius: 10px; border: 1px solid #e5e5e5; }
    button { display: none; }
    .title-delta { font-weight: 800; font-size: 2.5rem; text-align: center; color: #1a1a1a; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="title-delta">DELTA</h1>', unsafe_allow_html=True)
st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input(""):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Mise à jour mémoire (Logique Youtubeur : Silencieuse et robuste)
    try:
        update_prompt = f"Tu es un module de mémoire. Analyse: {prompt}. Archives actuelles: {archives}. Réponds uniquement en JSON formaté."
        memory_check = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Update memory JSON."}, {"role": "user", "content": update_prompt}],
            response_format={"type": "json_object"}
        )
        new_data = json.loads(memory_check.choices[0].message.content)
        if new_data:
            doc_ref.set({"archives": new_data}, merge=True)
            archives = new_data
    except:
        pass # Évite de bloquer la réponse en cas d'erreur de mémoire

    # Réponse DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        system_instruction = (
            f"Tu es DELTA. Créateur: Monsieur Sezer. Contexte: {archives}. "
            "Réponse ultra-courte. Pas de politesse. Info brute. "
            "Termine par 'Monsieur Sezer'."
        )

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_instruction}] + st.session_state.messages,
                temperature=0.2,
                stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_res += chunk.choices[0].delta.content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
        except Exception as e:
            st.error("Erreur de connexion au cerveau DELTA.")

        st.session_state.messages.append({"role": "assistant", "content": full_res})
