import os, json, requests, io
import streamlit as st

API_BASE = os.getenv("PA_API_BASE", "http://127.0.0.1:8000")

st.set_page_config(page_title="PA Assistant", page_icon="🩺", layout="wide")
st.title("🩺 Prior Authorization Assistant")

with st.sidebar:
    st.markdown("**API**: " + API_BASE)
    if st.button("Health check"):
        try:
            ok = requests.get(f"{API_BASE}/health", timeout=10).json()
            st.success(ok)
        except Exception as e:
            st.error(f"API not reachable: {e}")

st.subheader("1) Paste Clinical Note")
note_text = st.text_area(
    "Clinical note",
    height=350,
    placeholder="Paste the patient's clinical note here..."
)

col1, col2 = st.columns([1,1])
with col1:
    run = st.button("Generate Assessment")

with col2:
    st.caption("Tip: API must be running:  `uvicorn api.server:app --reload --port 8000`")

if run:
    if not note_text.strip():
        st.warning("Please paste a clinical note.")
        st.stop()
    try:
        with st.spinner("Assessing…"):
            resp = requests.post(
                f"{API_BASE}/assess",
                json={"note_text": note_text},
                timeout=60
            )
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        st.error(f"Request failed: {e}")
        st.stop()

    st.subheader("2) Decision")
    meets = data["decision"]["meets_criteria"]
    missing = data["decision"]["missing_information"]
    if meets:
        st.success("✅ Meets criteria")
    else:
        st.error("❌ More information needed")
        if missing:
            st.write("- " + "\n- ".join(missing))

    st.subheader("3) Summary (extracted)")
    st.json(data["summary"])

    st.subheader("4) Policy Citations")
    for c in data.get("citations", []):
        st.write(f"- **p.{c['page']}** — `{os.path.basename(c['source'])}`")
        st.caption(c["excerpt"])

    st.subheader("5) Medical Justification Letter")
    letter = data["justification_letter"]
    st.code(letter)

    # Download
    buf = io.BytesIO(letter.encode("utf-8"))
    st.download_button("Download Letter (.txt)", data=buf, file_name="justification.txt", mime="text/plain")
