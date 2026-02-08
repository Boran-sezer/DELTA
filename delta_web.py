import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, re

# --- CONFIGURATION ---
GROQ_API_KEY = "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"

# --- CONNEXION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur d'accès : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- CHARGEMENT DES ARCHIVES ---
res = doc_ref.get()
archives = res.to_dict() if res.exists else {}

# --- INTERFACE ---
st.set_page_config(page_title="DELTA", page_icon="🦾")
st.title("DELTA - Architecture Lux")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CORE ENGINE ---
if prompt := st.chat_input("Ordre direct..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. FILTRE LUX (8B pour détection rapide)
    check_prompt = f"Le message '{prompt}' contient-il une info capitale à mémoriser ? Réponds par OUI ou NON."
    check = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": check_prompt}]
    ).choices[0].message.content

    # 2. EXTRACTION LUX (70B pour structuration)
    if "OUI" in check.upper():
        brain_prompt = (
            f"ARCHIVES : {json.dumps(archives)}\n"
            f"MESSAGE : '{prompt}'\n"
            "MISSION : Extrais l'info et structure-la en JSON. "
            "Exemple : {'profil': {'age': 17}} ou {'projets': {'ia': 'en cours'}}. "
            "Réponds UNIQUEMENT en JSON."
        )
        
        analysis = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": "Extracteur JSON Lux."},
                      {"role": "user", "content": brain_prompt}],
            response_format={"type": "json_object"}
        ).choices[0].message.content
        
        try:
            new_data = json.loads(analysis)
            # Logique Lux : merge direct dans Firebase
            doc_ref.set(new_data, merge=True)
            # Mise à jour locale immédiate
            for k, v in new_data.items():
                if k not in archives: archives[k] = {}
                archives[k].update(v)
            st.toast("🧬 Synapse enregistrée.")
        except: pass

    # 3. RÉPONSE JARVIS
    with st.chat_message("assistant"):
        # Récupération dynamique du nom pour Jarvis
        nom_user = archives.get("profil", {}).get("nom", "Monsieur Sezer")
        
        sys_instr = (
            f"Tu es DELTA. Créateur : {nom_user}. "
            f"ARCHIVES : {json.dumps(archives)}. "
            "STYLE : Jarvis. Précis, dévoué, ultra-concis. "
            "Utilise les ARCHIVES pour personnaliser ta réponse."
        )
        
        res_ai = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-4:],
        ).choices[0].message.content
        
        st.markdown(res_ai)
        st.session_state.messages.append({"role": "assistant", "content": res_ai})
