import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json

# --- CONNEXION SIMPLE ---
if not firebase_admin._apps:
    encoded = st.secrets["firebase_key"]["encoded_key"].strip()
    decoded_json = base64.b64decode(encoded).decode("utf-8")
    cred = credentials.Certificate(json.loads(decoded_json))
    firebase_admin.initialize_app(cred)

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="VOTRE_CLE_GROQ")

st.title("DELTA - Mode Direct")

if prompt := st.chat_input("Dites n'importe quoi..."):
    # 1. ENVOI DIRECT À FIREBASE (Sans tri)
    try:
        doc_ref.set({"donnee_brute": prompt}, merge=True)
        st.success("Info envoyée à Firebase !")
    except Exception as e:
        st.error(f"Erreur : {e}")

    # 2. RÉPONSE IA SIMPLE
    chat_completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
    )
    st.write(f"DELTA : {chat_completion.choices[0].message.content}")
