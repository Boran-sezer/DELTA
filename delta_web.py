import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- 1. CONNEXION ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except: pass

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key="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")

# --- 2. DONNÉES ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA CORE", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA SYSTEM</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. TRAITEMENT ---
if prompt := st.chat_input("Ordres directs..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # A. ARCHIVAGE SILENCIEUX (Invisible & Précis)
    try:
        # On force l'IA à être très stricte sur l'identité
        task = f"Archives: {archives}. User: {prompt}. Extrais uniquement l'info capitale en JSON {{'CAT': 'VAL'}}. Si c'est l'identité, sois précis : Prénom = Boran, Nom = Sezer."
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Tu es un extracteur de données chirurgical."}, {"role": "user", "content": task}],
            response_format={"type": "json_object"}
        )
        data = json.loads(check.choices[0].message.content)
        if data:
            for cat, val in data.items():
                if cat not in archives: archives[cat] = []
                if val not in archives[cat]: archives[cat].append(val)
            doc_ref.set({"archives": archives})
    except: pass

    # B. RÉPONSE (Zéro message technique)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Consigne de personnalité stricte
        instruction = (
            f"Tu es DELTA. Tu parles à Monsieur Sezer Boran (Prénom: Boran, Nom: Sezer). "
            f"Archives : {archives}. "
            "INTERDICTION : Ne dis jamais 'Passage en mode léger'. "
            "INTERDICTION : Ne te trompe pas sur son nom. "
            "Réponds en français, sois froid, efficace et technique. Pas de politesses inutiles."
        )

        try:
            # On essaie le modèle puissant
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages,
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_res += content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
        except:
            # Si erreur quota, on passe au petit modèle SILENCIEUSEMENT
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages
            )
            full_res = resp.choices[0].message.content
            placeholder.markdown(full_res)

        st.session_state.messages.append({"role": "assistant", "content": full_res})
