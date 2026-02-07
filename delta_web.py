import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- 1. INITIALISATION ---
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

# --- 2. RÉCUPÉRATION MÉMOIRE ---
res = doc_ref.get()
archives = res.to_dict().get("archives", {}) if res.exists else {}

# --- 3. INTERFACE ---
st.set_page_config(page_title="DELTA CORE V2", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA : SYSTÈME NERVEUX</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: st.session_state.messages = []
for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("Ordres..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # A. MISE À JOUR DE LA MÉMOIRE (L'IA gère son propre rangement)
    try:
        # On lui demande de comparer le message avec l'existant pour corriger ou ajouter
        task = (
            f"Archives actuelles : {archives}. "
            f"Nouveau message : {prompt}. "
            "MISSION : Mets à jour les archives. Si une information change (ex: l'âge), remplace l'ancienne par la nouvelle. "
            "Retourne UNIQUEMENT l'objet JSON complet et mis à jour."
        )
        
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Tu es la mémoire vive de DELTA. Tu corriges et mets à jour les faits."}, {"role": "user", "content": task}],
            response_format={"type": "json_object"}
        )
        nouvelles_archives = json.loads(check.choices[0].message.content)
        
        # Si l'IA a modifié les archives, on enregistre
        if nouvelles_archives != archives:
            doc_ref.set({"archives": nouvelles_archives})
            archives = nouvelles_archives
            st.toast("💾 Mémoire synchronisée")
    except: pass

    # B. RÉPONSE DE DELTA
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Instructions pour une réponse naturelle sur les infos
        instruction = (
            f"Tu es DELTA, l'IA de Monsieur Sezer. Connaissances : {archives}. "
            "DIRECTIVES : "
            "1. Si Monsieur Sezer demande ce que tu sais sur lui, liste les infos de façon claire (liste ou phrases) sans parler des catégories techniques ou du JSON. "
            "2. Appelle-le toujours Monsieur Sezer. "
            "3. Sois bref, intelligent et percutant. Pas de politesses."
        )

        try:
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
            # Secours si quota atteint
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages
            )
            full_res = resp.choices[0].message.content
            placeholder.markdown(full_res)

        st.session_state.messages.append({"role": "assistant", "content": full_res})
