import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        creds_dict = json.loads(decoded_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception:
        st.error("⚠️ Système de Mémoire défaillant.")

db = firestore.client()
# Références aux documents
doc_chat = db.collection("memoire").document("chat_history")
doc_profil = db.collection("memoire").document("profil_monsieur")

# --- CONNEXION GROQ ---
client = Groq(api_key="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")

# --- CHARGEMENT DES DONNÉES ---
if "messages" not in st.session_state:
    # Charger l'historique récent
    res_chat = doc_chat.get()
    st.session_state.messages = res_chat.to_dict().get("history", []) if res_chat.exists else []

# Charger la "Fiche de Faits" (Mémoire Longue)
res_profil = doc_profil.get()
faits_connus = res_profil.to_dict().get("faits", []) if res_profil.exists else []

# --- INTERFACE ---
st.title("⚡ DELTA SYSTEM")
st.sidebar.title("🧠 Mémoire de DELTA")

if st.sidebar.button("🗑️ Effacer le chat (Pas la mémoire)"):
    st.session_state.messages = []
    doc_chat.set({"history": []})
    st.rerun()

st.sidebar.write("**Informations retenues :**")
for f in faits_connus:
    st.sidebar.info(f"📍 {f}")

# Affichage des messages
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# --- LOGIQUE DE RÉPONSE ---
if p := st.chat_input("Ordres, Monsieur ?"):
    # 1. Analyser si Monsieur donne une info à retenir
    if any(keyword in p.lower() for keyword in ["retiens que", "note que", "mémorise"]):
        faits_connus.append(p)
        doc_profil.set({"faits": faits_connus})
        st.sidebar.success("Fait enregistré !")

    # 2. Ajouter au chat
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"):
        st.markdown(p)

    # 3. Réponse de DELTA
    with st.chat_message("assistant"):
        # On injecte les FAITS dans le système sans qu'ils soient dans le chat
        contexte_faits = "Voici ce que tu sais de Monsieur Boran : " + ", ".join(faits_connus)
        instructions = {
            "role": "system", 
            "content": f"Tu es DELTA, créé par Monsieur Boran. {contexte_faits}. Tu es son majordome fidèle."
        }
        
        full_history = [instructions] + st.session_state.messages
        
        r = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=full_history
        )
        rep = r.choices[0].message.content
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})

    # 4. Sauvegarde du chat
    doc_chat.set({"history": st.session_state.messages})
