import streamlit as st
import glob
import os
from google import genai
from google.genai import types

st.set_page_config(
    page_title="Profesorul AI - PLIF",
    page_icon="👨‍🏫",
    layout="centered"
)

st.title("👨‍🏫 Profesorul AI – Îmbunățiri Funciare")
st.caption("Platformă interactivă de pregătire profesională în Irigații, Desecare-Drenaj, CES și Hidraulică.")

# --- 1. PRELUARE SECURIZATĂ A CHEII API ---
if "GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["GEMINI_API_KEY"].strip()
else:
    st.error("Cheia GEMINI_API_KEY nu este configurată în Streamlit Secrets!")
    st.stop()

client = genai.Client(api_key=api_key)

# --- 2. ÎNCĂRCAREA BAZEI DE CUNOȘTINȚE ---
@st.cache_data
def load_knowledge_base():
    full_context = ""
    kb_files = glob.glob("./KnowledgeBase_PLIF/**/*.md", recursive=True) + glob.glob("./*.md", recursive=True)
    for fpath in kb_files:
        if "README" in fpath:
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                filename = os.path.basename(fpath)
                full_context += f"\n\n--- [FIȘIER: {filename}] ---\n" + f.read()
        except Exception:
            pass
    return full_context if full_context else "Se utilizează cunoștințele generale din ingineria hidroameliorativă românească."

KB_CONTEXT = load_knowledge_base()

# --- 3. LISTARE DINAMICĂ A MODELELOR CANDIDATE ---
def get_candidate_models():
    """Generează o listă completă de modele posibile din contul utilizatorului."""
    candidates = []
    try:
        listed = [m.name.replace("models/", "") for m in client.models.list()]
        for name in listed:
            if name not in candidates:
                candidates.append(name)
    except Exception:
        pass

    defaults = [
        "gemini-2.0-flash-lite",
        "gemini-2.0-flash-001",
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro-latest",
        "gemini-2.0-pro-exp",
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ]
    for d in defaults:
        if d not in candidates:
            candidates.append(d)
            
    return candidates

# --- 4. GESTIONAREA ISTORICULUI DE CHAT ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# Afișarea mesajelor anterioare
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Prompt-ul utilizatorului
if prompt := st.chat_input("Adresează o întrebare Profesorului AI..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    system_instruction = f"""Ești un Profesor Universitar de Elită și Mentor în Ingineria Îmbunățirilor Funciare (PLIF) din România.
Ai la dispoziție Baza de Cunoștințe specializată:
{KB_CONTEXT[:8000]} [...]

Misiunea ta pedagogică:
1. Să explici noțiuni teoretice, tehnologii de exploatare, ecuații hidraulice (ex: Glover-Dumm, Penman-Monteith, curbe pompe) clar, concis și pedagogic.
2. Să răspunzi cu rigoare ingineriască ancorată în practica din România (norme ANIF, STAS-uri, condiții de teren).
3. Oferă exerciții practice de calcul numerice rezolvate pas cu pas sau grile de verificare când ți se cere.
4. Folosește notații LaTeX pentru toate formulele matematice/hidraulice."""

    formatted_history = []
    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "model"
        formatted_history.append(types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])]))

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Încercăm dinamic fiecare model până găsim unul funcțional
        model_candidates = get_candidate_models()
        success = False
        error_logs = []

        for model_id in model_candidates:
            try:
                response = client.models.generate_content(
                    model=model_id,
                    contents=formatted_history,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.2
                    )
                )
                if response and response.text:
                    full_response = response.text
                    message_placeholder.markdown(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    st.sidebar.success(f" Conectat cu succes la modelul: `{model_id}`")
                    success = True
                    break
            except Exception as e:
                error_logs.append(f"`{model_id}`: {str(e)[:100]}")
                continue

        if not success:
            st.error("Nu s-a putut conecta la niciun model Gemini. Detalii erori:")
            for err in error_logs[:3]:
                st.write(err)
