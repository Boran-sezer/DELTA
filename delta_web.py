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
    except: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")

# --- AUTHENTIFICATION GROQ ---
client = Groq(api_key="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")

# --- RÉCUPÉRATION MÉMOIRE ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- INTERFACE BLANCHE ET SOBRE ---
st.set_page_config(page_title="DELTA", layout="wide")
st.markdown("""
    <style>
    .stApp { background: #ffffff; color: #1a1a1a; }
    .stChatMessage { background-color: #f7f7f8; border-radius: 10px; border: 1px solid #e5e5e5; margin-bottom: 10px; }
    button { display: none; }
    .stChatInputContainer { background: #ffffff !important; border-top: 1px solid #eeeeee; }
    p { color: #1a1a1a !important; font-family: 'Inter', sans-serif; }
    </style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- LOGIQUE PRINCIPALE ---
if prompt := st.chat_input(""):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Mise à jour mémoire
    try:
        task = f"Archives: {archives}. Info: {prompt}. Update JSON."
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Memory update only. JSON output."}, {"role": "user", "content": task}],
            response_format={"type": "json_object"}
        )
        nouvelles_archives = json.loads(check.choices[0].message.content)
        if nouvelles_archives != archives:
            doc_ref.set({"archives": nouvelles_archives})
            archives = nouvelles_archives
    except: pass

    # Réponse DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        instruction = (
            f"Tu es DELTA. Créateur: Monsieur Sezer. Data: {archives}. "
            "DIRECTIVES: Réponse ultra-courte. Pas d'intro. Pas de politesse. "
            "Donne l'info brute. Nomme l'utilisateur Monsieur Sezer à la fin."
        )

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages,
                temperature=0.0,
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_res += content
                    placeholder.markdown(full_res)
        except Exception as e:
            st.error(f"Erreur : {e}")

        st.session_state.messages.append({"role": "assistant", "content": full_res})
