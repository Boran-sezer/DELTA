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
st.set_page_config(page_title="DELTA AI - Autonome", layout="wide")
st.markdown("<h1 style='color:#00d4ff;'>⚡ SYSTEME DELTA : MODE AUTONOME</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("Dites n'importe quoi, Monsieur Sezer..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # --- CYCLE DE PENSÉE AUTONOME (INVISIBLE) ---
    # DELTA décide seul s'il doit modifier sa mémoire
    sys_analyse = (
        f"Tu es le cerveau autonome de Monsieur Sezer. Voici ta mémoire actuelle : {archives}. "
        f"Il vient de dire : '{prompt}'. "
        "Si ce message contient une info utile, une correction d'un fait ancien ou une demande de suppression implicite, "
        "réponds UNIQUEMENT avec l'objet JSON complet et mis à jour de la mémoire. "
        "Sois proactif : crée des sections, reformule proprement, et supprime les contradictions. "
        "Si rien ne mérite d'être changé, réponds exactement par le mot : IGNORE."
    )
    
    try:
        check = client.chat.completions.create(
            model="llama-3.3-70b-versatile", 
            messages=[{"role": "system", "content": "Tu es une mémoire vive autonome."}, {"role": "user", "content": sys_analyse}],
            temperature=0
        )
        verdict = check.choices[0].message.content.strip()
        
        if verdict != "IGNORE":
            # Extraction du JSON au cas où l'IA ajoute du texte par erreur
            match = re.search(r'\{.*\}', verdict, re.DOTALL)
            if match:
                nouvelles_archives = json.loads(match.group(0))
                if nouvelles_archives != archives:
                    archives = nouvelles_archives
                    doc_ref.set({"archives": archives})
                    st.toast("🧠 Mémoire auto-mise à jour")
    except: pass

    # --- 5. RÉPONSE DE DELTA ---
    with st.chat_message("assistant"):
        instruction_delta = (
            f"Tu es DELTA. Tu parles à Monsieur Sezer Boran. "
            f"Connaissances actuelles : {archives}. "
            "Réponds de manière technique et concise. Ne mentionne pas que tu mets à jour ta mémoire sauf si on te le demande."
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
