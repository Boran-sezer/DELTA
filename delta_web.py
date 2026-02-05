import streamlit as st
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore
import base64
import json

# --- CONFIGURATION ---
st.set_page_config(page_title="DELTA OS", page_icon="⚡", layout="wide")

# --- INITIALISATION FIREBASE ---
if not firebase_admin._apps:
    try:
        encoded = st.secrets["firebase_key"]["encoded_key"].strip()
        decoded_json = base64.b64decode(encoded).decode("utf-8")
        creds_dict = json.loads(decoded_json)
        cred = credentials.Certificate(creds_dict)
        firebase_admin.initialize_app(cred)
    except Exception:
        st.error("⚠️ Connexion Mémoire interrompue.")

db = firestore.client()
doc_profil = db.collection("memoire").document("profil_monsieur")

# --- CONNEXION GROQ ---
client = Groq(api_key="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")

# --- ÉTATS DE SESSION ---
if "code_requis" not in st.session_state: st.session_state.code_requis = False
if "action_type" not in st.session_state: st.session_state.action_type = None
if "info_temporaire" not in st.session_state: st.session_state.info_temporaire = None
if "unlocked" not in st.session_state: st.session_state.unlocked = False

# --- CHARGEMENT DU PROFIL ---
res_profil = doc_profil.get()
data = res_profil.to_dict() if res_profil.exists else {}
faits_publics = data.get("faits", [])
faits_verrouilles = data.get("faits_verrouilles", [])

# --- INTERFACE ---
st.title("⚡ DELTA SYSTEM")

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.title("🧠 Archives")
    st.subheader("Standard")
    for i, f in enumerate(faits_publics):
        col1, col2 = st.columns([4, 1])
        col1.info(f"{f}")
        if col2.button("🗑️", key=f"p_{i}"):
            faits_publics.pop(i)
            doc_profil.update({"faits": faits_publics})
            st.rerun()
    
    st.subheader("🔐 Scellées")
    if st.session_state.unlocked:
        for i, f in enumerate(faits_verrouilles):
            col1, col2 = st.columns([4, 1])
            col1.warning(f"{f}")
            if col2.button("🗑️", key=f"s_{i}"):
                faits_verrouilles.pop(i)
                doc_profil.update({"faits_verrouilles": faits_verrouilles})
                st.rerun()
        if st.button("Fermer le coffre"):
            st.session_state.unlocked = False
            st.rerun()
    else:
        st.write("Accès verrouillé.")

# --- FORMULAIRE DE CODE PRIORITAIRE ---
if st.session_state.code_requis:
    with st.form("security_form"):
        st.warning("🔒 AUTHENTIFICATION REQUISE - CODE 20082008")
        code_input = st.text_input("Entrez le code d'autorisation :", type="password")
        submit = st.form_submit_button("VALIDER")
        
        if submit:
            if code_input == "20082008":
                if st.session_state.action_type == "reset_all":
                    doc_profil.set({"faits": [], "faits_verrouilles": []})
                    st.success("Toutes les données ont été purgées, Monsieur.")
                elif st.session_state.action_type == "reset_target":
                    t = st.session_state.info_temporaire.lower()
                    faits_publics = [f for f in faits_publics if t not in f.lower()]
                    faits_verrouilles = [f for f in faits_verrouilles if t not in f.lower()]
                    doc_profil.set({"faits": faits_publics, "faits_verrouilles": faits_verrouilles})
                    st.success(f"Cibles éliminées.")
                elif st.session_state.action_type == "lock":
                    faits_verrouilles.append(st.session_state.info_temporaire)
                    doc_profil.update({"faits_verrouilles": faits_verrouilles})
                    st.success("Information scellée.")
                elif st.session_state.action_type == "unlock":
                    st.session_state.unlocked = True
                
                st.session_state.code_requis = False
                st.session_state.action_type = None
                st.rerun()
            else:
                st.error("Code erroné. Procédure annulée.")
                st.session_state.code_requis = False
                st.rerun()
    st.stop() # Arrête le reste de l'app tant que le formulaire est là

# --- LOGIQUE CHAT ---
if "messages" not in st.session_state: st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]): st.markdown(m["content"])

if p := st.chat_input("Ordres ?"):
    st.session_state.messages.append({"role": "user", "content": p})
    with st.chat_message("user"): st.markdown(p)

    rep = ""
    low_p = p.lower()
    
    if "réinitialisation complète" in low_p:
        st.session_state.code_requis = True
        st.session_state.action_type = "reset_all"
        rep = "Protocole de purge totale activé. En attente du code."
    elif "supprime précisément" in low_p:
        st.session_state.code_requis = True
        st.session_state.action_type = "reset_target"
        st.session_state.info_temporaire = p.replace("supprime précisément", "").strip()
        rep = "Cible identifiée. En attente du code pour suppression."
    elif "verrouille" in low_p:
        st.session_state.code_requis = True
        st.session_state.action_type = "lock"
        st.session_state.info_temporaire = p.replace("verrouille", "").strip()
        rep = "Préparation du scellage. Code requis."
    elif "affiche les archives verrouillées" in low_p:
        st.session_state.code_requis = True
        st.session_state.action_type = "unlock"
        rep = "Accès au coffre-fort. Code requis."
    else:
        with st.chat_message("assistant"):
            ctx = f"Infos publiques: {faits_publics}. Infos scellées: {faits_verrouilles}."
            instr = {"role": "system", "content": f"Tu es DELTA, majordome de Monsieur Boran. {ctx}"}
            r = client.chat.completions.create(model="llama-3.3-70b-versatile", messages=[instr] + st.session_state.messages)
            rep = r.choices[0].message.content

    with st.chat_message("assistant"):
        st.markdown(rep)
        st.session_state.messages.append({"role": "assistant", "content": rep})
        if st.session_state.code_requis: st.rerun() # Pour afficher le formulaire immédiatement
