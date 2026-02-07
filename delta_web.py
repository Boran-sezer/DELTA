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
st.set_page_config(page_title="DELTA CORE V2.2", layout="wide", page_icon="⚡")
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
        task = (
            f"Archives actuelles : {archives}. "
            f"Nouveau message : {prompt}. "
            "DATE ACTUELLE : 2026. "
            "MISSION : Analyse le message. Si Monsieur Sezer donne une info personnelle (nom, âge, date), "
            "écrase l'ancienne valeur. Ignore les questions sur tes origines ici. "
            "Retourne UNIQUEMENT le JSON complet."
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
            st.toast("💾 Mémoire synchronisée", icon="✅")
    except: pass

    # B. GÉNÉRATION DE LA RÉPONSE (Conscience de soi corrigée)
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_res = ""
        
        # DEFINITION DE L'IDENTITE DE DELTA
        instruction = (
            f"Tu es DELTA, une IA de haut niveau. Ton créateur est Monsieur Sezer. "
            f"Données mémorisées sur Monsieur Sezer : {archives}. "
            "DATE SYSTÈME : 2026. "
            "RÈGLES D'OR : "
            "1. CRÉATEUR : Si on te demande qui t'a créé ou qui est ton patron, réponds : 'C'est Monsieur Sezer'. "
            "2. IDENTITÉ : Appelle l'utilisateur 'Monsieur Sezer'. "
            "3. STYLE : Ton froid, efficace, sans fioritures inutiles. "
            "4. ERREURS : Ne contredis jamais Monsieur Sezer sur ses propres informations (âge, naissance)."
        )

        try:
            stream = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages,
                temperature=0.3,
                stream=True
            )
            for chunk in stream:
                content = chunk.choices[0].delta.content
                if content:
                    full_res += content
                    placeholder.markdown(full_res + "▌")
            placeholder.markdown(full_res)
        except:
            # Fallback
            resp = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "system", "content": instruction}] + st.session_state.messages
            )
            full_res = resp.choices[0].message.content
            placeholder.markdown(full_res)

        st.session_state.messages.append({"role": "assistant", "content": full_res})
