import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- 1. INITIALISATION FIREBASE & API ---
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
st.set_page_config(page_title="DELTA CORE V2.1", layout="wide", page_icon="⚡")
st.markdown("<h1 style='color:#00d4ff;'>⚡ DELTA : CORE SYSTEM (STABLE)</h1>", unsafe_allow_html=True)

if "messages" not in st.session_state: 
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- 4. LOGIQUE DE TRAITEMENT ---
if prompt := st.chat_input("Ordres directs..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # A. GESTION DE MÉMOIRE (Strict & Factuel)
    try:
        # On définit 2026 comme année de référence pour tout le système
        task = (
            f"Archives actuelles : {archives}. "
            f"Nouveau message : {prompt}. "
            "DATE ACTUELLE : 2026. "
            "MISSION : Analyse le message. Si Monsieur Sezer donne une info (nom, âge, date de naissance), "
            "écrase systématiquement l'ancienne valeur par la nouvelle. "
            "Ignore les salutations. Retourne UNIQUEMENT le JSON complet."
        )
        
        check = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "Tu es le processeur de faits de DELTA. Tu ne discutes pas, tu enregistres."}, {"role": "user", "content": task}],
            response_format={"type": "json_object"}
        )
        nouvelles_archives = json.loads(check.choices[0].message.content)
        
        if nouvelles_archives != archives:
            doc_ref.set({"archives": nouvelles_archives})
            archives = nouvelles_archives
            st.toast("💾 Base de données synchronisée", icon="✅")
    except: pass

    # B. GÉNÉRATION DE LA RÉPONSE
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # Instruction avec Date Système 2026 verrouillée
        instruction = (
            f"Tu es DELTA. Tu parles à Monsieur Sezer. "
            f"Données connues : {archives}. "
            "CONTEXTE TEMPOREL : Nous sommes en 2026. "
            "DIRECTIVES : "
            "1. Ne remets JAMAIS en question les affirmations de Monsieur Sezer sur son âge ou sa date de naissance. "
            "2. Ne montre jamais tes calculs. Réponds de façon directe. "
            "3. STYLE : Ton froid, supérieur, technique. Pas de politesses. "
            "4. NOM : Appelle-le uniquement 'Monsieur Sezer'."
        )

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages,
                temperature=0.3, # Réduit pour plus de stabilité/précision
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_res += content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
        except:
            # Secours
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages
            )
            full_res = resp.choices[0].message.content
            placeholder.markdown(full_res)

        st.session_state.messages.append({"role": "assistant", "content": full_res})
