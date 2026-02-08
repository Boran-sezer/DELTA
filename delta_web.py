import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, re
from datetime import datetime

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
        st.error(f"Erreur : {e}")

db = firestore.client()
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- CHARGEMENT SÉCURISÉ (ANTI-KEYERROR) ---
res = doc_ref.get()
if res.exists:
    archives = res.to_dict()
else:
    # Structure par défaut si le document est vide
    archives = {
        "identite": {"nom": "Monsieur Sezer"},
        "projets": {},
        "preferences": {},
        "logs": []
    }

# --- INTERFACE ---
st.title("DELTA - Architecture Lux")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

# --- CORE ENGINE ---
if prompt := st.chat_input("Ordre..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. LE FILTRE SYNAPTIQUE
    filtre_prompt = (
        f"ANALYSE : '{prompt}'. "
        "Si info capitale (âge, nom, projet), réponds UNIQUEMENT en JSON : "
        "{'identite': {'age': 17}, 'projets': {'nom': 'ia'}}. Sinon réponds 'RIEN'."
    )
    
    analysis = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[{"role": "system", "content": "Extracteur JSON pur."},
                  {"role": "user", "content": filtre_prompt}]
    ).choices[0].message.content

    if "RIEN" not in analysis:
        match = re.search(r'\{.*\}', analysis, re.DOTALL)
        if match:
            try:
                new_data = json.loads(match.group().replace("'", '"'))
                doc_ref.set(new_data, merge=True)
                # Mise à jour locale pour la réponse immédiate
                for k, v in new_data.items():
                    if k in archives: archives[k].update(v)
                st.toast("🧬 Mémoire synchronisée")
            except: pass

    # 2. RÉPONSE IA
    with st.chat_message("assistant"):
        # Sécurité supplémentaire : .get() avec valeur par défaut
        nom_user = archives.get('identite', {}).get('nom', 'Monsieur Sezer')
        
        sys_instr = (
            f"Tu es DELTA. Créateur : {nom_user}. "
            f"MÉMOIRE : {json.dumps(archives)}. "
            "Ton : Jarvis. Précis, dévoué, extrêmement concis."
        )
        
        full_res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": sys_instr}] + st.session_state.messages[-6:],
        ).choices[0].message.content
        
        st.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
