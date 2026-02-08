import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64, json, re

# --- CONFIGURATION ---
GROQ_API_KEY = "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"

# --- CONNEXION ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        cred = credentials.Certificate(json.loads(decoded_json))
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur clé : {e}")

db = firestore.client()
# On utilise la collection 'archives' comme Lux
doc_ref = db.collection("archives").document("monsieur_sezer")
client = Groq(api_key=GROQ_API_KEY)

# --- VERIFICATION CONNEXION ---
try:
    doc_ref.set({"derniere_connexion": "online"}, merge=True)
    st.sidebar.success("✅ Firebase Connecté")
except:
    st.sidebar.error("❌ Firebase Bloqué (Vérifiez les Règles)")

# --- LOGIQUE DE MÉMOIRE ---
res = doc_ref.get()
cerveau = res.to_dict() if res.exists else {"identite": {}, "projets": {}, "preferences": {}}

st.title("DELTA")

if prompt := st.chat_input("Dites : 'J'ai 18 ans'"):
    # 1. LE TRIEUR (Filtre Lux)
    extraction_prompt = (
        f"Analyse : '{prompt}'. Si info cruciale, réponds UNIQUEMENT en JSON : "
        "{'identite': {'age': 18}}. Sinon réponds 'RIEN'."
    )
    
    trieur_res = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[{"role": "user", "content": extraction_prompt}]
    ).choices[0].message.content

    if "RIEN" not in trieur_res:
        match = re.search(r'\{.*\}', trieur_res, re.DOTALL)
        if match:
            try:
                infos = json.loads(match.group().replace("'", '"'))
                doc_ref.set(infos, merge=True)
                st.toast("Mémoire mise à jour !")
            except: pass

    # 2. RÉPONSE
    sys_instr = f"Tu es DELTA. Tu sais ça de Monsieur Sezer : {cerveau}. Sois très bref."
    res_ai = client.chat.completions.create(
        messages=[{"role": "system", "content": sys_instr}, {"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
    ).choices[0].message.content
    
    with st.chat_message("assistant"):
        st.write(res_ai)
