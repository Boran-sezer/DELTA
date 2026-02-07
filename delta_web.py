import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json
import re

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
st.set_page_config(page_title="DELTA AI - Optimized", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("En attente de vos ordres..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # --- ARCHIVISTE (MODÈLE LÉGER POUR ÉCONOMISER LE QUOTA) ---
    try:
        sys_analyse = (
            f"Tu es l'unité de gestion de données de Monsieur Sezer Boran. Mémoire : {archives}. "
            f"Dernier message : '{prompt}'. "
            "Réponds UNIQUEMENT avec l'objet JSON complet des archives mis à jour."
        )
        # On utilise le modèle 8B ici (10x plus de quota disponible)
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant", 
            messages=[{"role": "system", "content": "Moteur JSON."}, {"role": "user", "content": sys_analyse}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        verdict = check.choices[0].message.content
        nouvelles_archives = json.loads(verdict)
        if nouvelles_archives != archives:
            doc_ref.set({"archives": nouvelles_archives})
            archives = nouvelles_archives
            st.toast("⚙️ Sync")
    except:
        pass 

    # --- 5. RÉPONSE DE DELTA (MODÈLE PUISSANT) ---
    with st.chat_message("assistant"):
        instruction_delta = (
            f"Tu es DELTA. Tu parles à Monsieur Sezer Boran. "
            f"Connaissances : {archives}. "
            "Réponds en FRANÇAIS, bref, technique. Pas de JSON."
        )
        
        placeholder = st.empty()
        full_response = ""
        
        try:
            # On garde le 70B ici pour la qualité de la réponse
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages,
                stream=True
            )
            
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_response += content
                    placeholder.markdown(full_response + "▌")
            
            placeholder.markdown(full_response)
        except Exception as e:
            if "rate_limit" in str(e).lower():
                st.error("⚠️ Quota Groq atteint. DELTA doit se reposer quelques minutes.")
            else:
                st.error(f"Erreur : {e}")
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})
