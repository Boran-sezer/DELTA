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
st.set_page_config(page_title="DELTA AI - R1 Fixed", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA : DEEP REASONING + FIREBASE</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("Ordres, Monsieur Sezer..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # --- ANALYSEUR DE MÉMOIRE (DEEPSEEK R1) ---
    sys_analyse = (
        f"Tu es le cerveau de Monsieur Sezer. Mémoire actuelle : {archives}. "
        f"Dernière interaction : '{prompt}'. "
        "Tu DOIS extraire chaque fait important et mettre à jour le JSON. "
        "Produis UNIQUEMENT le code JSON final des archives. Pas de texte avant ou après."
    )
    
    try:
        check = client.chat.completions.create(
            model="deepseek-r1-distill-llama-70b", 
            messages=[{"role": "system", "content": "Tu es un expert en structuration de données JSON."}, {"role": "user", "content": sys_analyse}],
            temperature=0.1
        )
        verdict = check.choices[0].message.content
        
        # Correction : On nettoie les balises <think> et on cherche le JSON
        nettoye = re.sub(r'<think>.*?</think>', '', verdict, flags=re.DOTALL)
        json_match = re.search(r'\{.*\}', nettoye, re.DOTALL)
        
        if json_match:
            nouvelles_archives = json.loads(json_match.group(0))
            if nouvelles_archives != archives:
                # Mise à jour Firebase
                doc_ref.set({"archives": nouvelles_archives})
                archives = nouvelles_archives
                st.toast("💾 Firebase mis à jour avec succès")
    except Exception as e:
        st.error(f"Erreur d'archivage : {e}")

    # --- 5. RÉPONSE DE DELTA ---
    with st.chat_message("assistant"):
        instruction_delta = (
            f"Tu es DELTA. Tu parles à Monsieur Sezer Boran. "
            f"Archives Firebase : {archives}. "
            "Sois percutant, technique et efficace."
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
        except: placeholder.markdown("Erreur de liaison.")
        st.session_state.messages.append({"role": "assistant", "content": full_response})
