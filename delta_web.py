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
st.title("DELTA - Système Stable")

if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if prompt := st.chat_input("Ordre..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"): st.markdown(prompt)

    # 1. SAUVEGARDE HISTORIQUE
    try:
        doc_ref.update({"historique": firestore.ArrayUnion([prompt])})
    except:
        doc_ref.set({"historique": [prompt]}, merge=True)

    # 2. EXTRACTION AVEC SÉCURITÉ JSON
    extraction_prompt = (
        f"Analyse : '{prompt}'. Si info cruciale (âge, projet), "
        "réponds UNIQUEMENT avec un JSON pur : {'cle': 'valeur'}. "
        "Sinon réponds 'RIEN'."
    )
    
    check_res = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[{"role": "user", "content": extraction_prompt}]
    ).choices[0].message.content

    if "RIEN" not in check_res:
        match = re.search(r'\{.*\}', check_res, re.DOTALL)
        if match:
            try:
                # Nettoyage des caractères invisibles pour éviter l'erreur JSON
                clean_json = match.group().replace("'", '"')
                infos_cruciales = json.loads(clean_json)
                doc_ref.set({"biographie": infos_cruciales}, merge=True)
            except json.JSONDecodeError:
                pass # On ignore si le JSON est corrompu pour éviter le crash

    # 3. RÉPONSE IA
    with st.chat_message("assistant"):
        bio = memoire.get("biographie", {})
        sys_instr = f"Tu es DELTA. Créateur : Monsieur Sezer. Mémoire : {bio}. Sois concis."
        
        full_res = client.chat.completions.create(
            messages=[{"role": "system", "content": sys_instr}, {"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
        ).choices[0].message.content
        st.markdown(full_res)
        st.session_state.messages.append({"role": "assistant", "content": full_res})
