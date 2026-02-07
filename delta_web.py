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
st.set_page_config(page_title="DELTA AI - Haute Précision", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA : ARCHIVAGE CRITIQUE</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("Transmettez vos données, Monsieur Sezer..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # --- ANALYSEUR HAUTE PERFORMANCE (INVISIBLE) ---
    sys_analyse = (
        f"Tu es le centre de données de Monsieur Sezer. Mémoire actuelle : {archives}. "
        f"Dernier message : '{prompt}'. "
        "MISSION : Identifie CHAQUE information cruciale (technique, personnelle, projet, préférence). "
        "Ne jette rien d'important. Reformule pour que ce soit clair et professionnel. "
        "Réorganise les sections si nécessaire. "
        "Réponds EXCLUSIVEMENT avec l'objet JSON complet mis à jour. "
        "Si absolument rien de nouveau ou d'utile n'est détecté, réponds : IGNORE."
    )
    
    try:
        # Utilisation du modèle 70B pour l'analyse de mémoire
        check = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "system", "content": "Tu es un expert en gestion de données stratégiques."}, {"role": "user", "content": sys_analyse}],
            temperature=0
        )
        verdict = check.choices[0].message.content.strip()
        
        if verdict != "IGNORE":
            match = re.search(r'\{.*\}', verdict, re.DOTALL)
            if match:
                nouvelles_archives = json.loads(match.group(0))
                if nouvelles_archives != archives:
                    archives = nouvelles_archives
                    doc_ref.set({"archives": archives})
                    st.toast("⚙️ Données critiques archivées")
    except: pass

    # --- 5. RÉPONSE DE DELTA ---
    with st.chat_message("assistant"):
        instruction_delta = (
            f"Tu es DELTA. Créateur : Monsieur Sezer Boran. "
            f"Données mémorisées : {archives}. "
            "Sois ultra-précis, technique et efficace. Utilise les archives pour chaque réponse."
        )
        placeholder = st.empty()
        full_response = ""
        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile", 
                messages=[{"role": "system", "content": instruction_delta}] + st.session_state.messages,
                temperature=0.3, stream=True
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    placeholder.markdown(full_response + "▌")
            placeholder.markdown(full_response)
        except: placeholder.markdown("Erreur.")
        st.session_state.messages.append({"role": "assistant", "content": full_response})
