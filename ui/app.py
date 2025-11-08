import os, json, io, sys
import streamlit as st

# Add parent directory to path so we can import from rag/ and app/
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import functions with correct names
try:
    from rag.clinical_extractor import extract_patient_summary
    from app.eligibility import evaluate_icgm
    from app.justification import build_justification_letter
except ImportError as e:
    st.error(f"Import error: {e}. Make sure rag and app modules are available.")
    st.exception(e)
    st.stop()

st.set_page_config(page_title="PA Assistant", page_icon="🩺", layout="wide")
st.title("🩺 Prior Authorization Assistant")
st.markdown("*AI-driven automation for healthcare prior authorization workflows*")

with st.sidebar:
    st.markdown("### About")
    st.markdown("""
    This system uses:
    - **RAG** for policy retrieval
    - **Gemini API** for clinical extraction
    - **Rule-based** eligibility logic
    """)
    st.markdown("---")
    st.markdown("**Demo Mode**: Standalone (no API needed)")
    
    # Add example button
    if st.button("📝 Load Example Patient"):
        st.session_state['example_note'] = """Patient ID: 12345
Name: Jane Doe
Age: 56 years
Gender: Female
Date: November 7, 2025

Chief Complaint: Poorly controlled Type 1 Diabetes requesting Continuous Glucose Monitor

Diagnosis:
- Type 1 Diabetes Mellitus (ICD-10: E10.9)
- Hypoglycemia unawareness

Laboratory Results:
- HbA1c: 9.2% (last 3 months average)
- Fasting glucose: 180 mg/dL
- Recent hypoglycemic episodes: 3 in past month

Current Medications:
- Insulin glargine (Lantus) 20 units subcutaneously at bedtime
- Insulin aspart (NovoLog) 6 units before meals
- Metformin 1000mg twice daily

Blood Glucose Monitoring:
- Self-monitoring blood glucose (SMBG) ≥4 times per day
- Documented hypoglycemia events requiring assistance
- Frequent nocturnal hypoglycemia

Clinical Rationale:
Patient demonstrates poor glycemic control despite intensive insulin therapy and frequent self-monitoring. HbA1c remains elevated at 9.2% despite compliance with current regimen. Patient experiences hypoglycemia unawareness with documented episodes requiring third-party assistance. Continuous glucose monitoring is medically necessary to improve glycemic control and reduce risk of severe hypoglycemic events.

Requested Device: Continuous Glucose Monitor (CGM) - I-CGM System"""

st.subheader("1) Paste Clinical Note")

# Use example note if loaded
default_text = st.session_state.get('example_note', '')

note_text = st.text_area(
    "Clinical note",
    value=default_text,
    height=350,
    placeholder="Paste the patient's clinical note here... or click 'Load Example Patient' in the sidebar"
)

col1, col2 = st.columns([1,2])
with col1:
    run = st.button("Generate Assessment", type="primary")

with col2:
    st.caption("💡 Tip: Try the example patient in the sidebar")

if run:
    if not note_text.strip():
        st.warning("Please paste a clinical note.")
        st.stop()
    
    try:
        with st.spinner("🔍 Extracting patient data..."):
            # Step 1: Extract patient data using Gemini (returns dict)
            summary = extract_patient_summary(note_text)
        
        with st.spinner("✅ Assessing eligibility..."):
            # Step 2: Assess eligibility (returns tuple: bool, list)
            meets_criteria, missing_info = evaluate_icgm(summary)
        
        with st.spinner("📝 Generating justification letter..."):
            # Step 3: Generate justification letter
            # Mock policy hits for demo (no vector retrieval in cloud)
            mock_hits = [{
                "document": "Continuous glucose monitoring is medically necessary for patients with Type 1 diabetes who meet criteria including HbA1c >7%, intensive insulin therapy, and documented hypoglycemia.",
                "metadata": {"source": "CGM_Policy.pdf", "page": 3}
            }]
            
            justification_letter = build_justification_letter(
                summary=summary,
                meets_criteria=meets_criteria,
                missing_information=missing_info,
                policy_hits=mock_hits
            )
        
        # Display results
        st.success("✨ Assessment complete!")
        
        st.subheader("2) Decision")
        
        if meets_criteria:
            st.success("✅ Eligible - Meets criteria for CGM")
        else:
            st.warning("⚠️ More information needed")
            if missing_info:
                st.write("**Missing information:**")
                for item in missing_info:
                    st.write(f"- {item}")

        st.subheader("3) Patient Summary (Extracted)")
        
        # Display in nice formatted way
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Demographics**")
            st.write(f"Patient ID: {summary.get('patient_id', 'N/A')}")
            st.write(f"Age: {summary.get('age', 'N/A')}")
            st.write(f"Sex: {summary.get('sex', 'N/A')}")
            
            st.markdown("**Diagnoses**")
            diagnoses = summary.get('diagnoses', [])
            if diagnoses:
                for dx in diagnoses:
                    code = dx.get('code', 'N/A')
                    desc = dx.get('description', 'N/A')
                    st.write(f"- {desc} ({code})")
            else:
                st.write("No diagnoses extracted")
        
        with col2:
            st.markdown("**Labs**")
            labs = summary.get('labs', [])
            if labs:
                for lab in labs:
                    name = lab.get('name', 'N/A')
                    value = lab.get('value', 'N/A')
                    unit = lab.get('unit', '')
                    st.write(f"- {name}: {value} {unit}")
            else:
                st.write("No labs extracted")
            
            st.markdown("**Medications**")
            meds = summary.get('meds', [])
            if meds:
                for med in meds:
                    st.write(f"- {med.get('name', 'N/A')}")
            else:
                st.write("No medications extracted")

        # Show raw JSON in expander
        with st.expander("📄 View Raw JSON"):
            st.json(summary)

        st.subheader("4) Policy Citations")
        st.info("💡 Policy retrieval is simplified in the cloud demo. In production, this would show relevant insurance policy excerpts from the vector database.")
        
        # Show mock citations
        st.write("- **p.3** — `CGM_Coverage_Policy.pdf`")
        st.caption("Continuous glucose monitoring is medically necessary for patients with Type 1 diabetes who meet the following criteria: HbA1c >7%, intensive insulin therapy, and documented hypoglycemia...")

        st.subheader("5) Medical Justification Letter")
        st.code(justification_letter, language="text")

        # Download button
        buf = io.BytesIO(justification_letter.encode("utf-8"))
        st.download_button(
            "⬇️ Download Letter (.txt)", 
            data=buf, 
            file_name="justification_letter.txt", 
            mime="text/plain",
            type="primary"
        )
        
    except Exception as e:
        st.error(f"❌ Error during assessment: {str(e)}")
        st.exception(e)
        st.stop()

# Footer
st.markdown("---")
st.caption("Built with Streamlit • Powered by Gemini API • RAG-based Policy Retrieval")