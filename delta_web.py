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
        st.error(f"Erreur Firebase : {e}")

db = firestore.client()
doc_ref = db.collection("memoire").document("profil_monsieur")
client = Groq(api_key=GROQ_API_KEY)

# --- CHARGEMENT ---
res = doc_ref.get()
memoire = res.to_dict() if res.exists else {"biographie": {}, "historique": []}

# --- INTERFACE ---
st.title("DELTA - Mémoire Sélective")

if prompt := st.chat_input("Ordre..."):
    # 1. SAUVEGARDE DANS L'HISTORIQUE (BRUT)
    doc_ref.update({"historique": firestore.ArrayUnion([prompt])})

    # 2. EXTRACTION DES INFOS CRUCIALES (FILTRE)
    extraction_prompt = (
        f"Voici un message : '{prompt}'. Si ce message contient une info importante "
        "(ex: âge, nom, passion, ville), extrais-la en JSON pur sous cette forme : "
        "{'age': 18, 'nom': 'Sezer'}. Sinon réponds 'RIEN'."
    )
    
    check = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[{"role": "user", "content": extraction_prompt}]
    ).choices[0].message.content

    if "RIEN" not in check:
        match = re.search(r'\{.*\}', check, re.DOTALL)
        if match:
            infos_cruciales = json.loads(match.group())
            # On range les infos cruciales dans le dossier 'biographie' pour ne pas les perdre
            doc_ref.set({"biographie": infos_cruciales}, merge=True)

    # 3. RÉPONSE IA
    with st.chat_message("assistant"):
        # On donne à DELTA uniquement les infos cruciales pour qu'il soit efficace
        bio = memoire.get("biographie", {})
        sys_instr = f"Tu es DELTA. Ton créateur est Monsieur Sezer. Tu sais ça de lui : {bio}. Sois concis."
        
        res_ai = client.chat.completions.create(
            messages=[{"role": "system", "content": sys_instr}, {"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        ).choices[0].message.content
        st.write(res_ai)
