import streamlit as st
import os
import tempfile
import pandas as pd
from typing import List

from main import build_pipeline, detect_pii, assign_replacements
from src.core.entity import PIIEntity

# Streamlit App Configuration
st.set_page_config(
    page_title="PII Redaction Tool",
    page_icon="🛡️",
    layout="wide"
)

st.title("🛡️ PII Redaction Web Interface")
st.markdown("Upload a DOCX file to detect and redact Personally Identifiable Information (PII) using our hybrid detection pipeline.")

# Initialize the pipeline once
@st.cache_resource
def get_pipeline():
    return build_pipeline()

(regex_detector, ner_detector, context_detector, 
 merger, scorer, registry, replacement_gen, docx_processor) = get_pipeline()

# Sidebar for configuration
with st.sidebar:
    st.header("Settings")
    threshold = st.slider("Confidence Threshold", min_value=0.5, max_value=1.0, value=0.85, step=0.05, 
                          help="Minimum confidence score required to redact an entity.")

# File Uploader
uploaded_file = st.file_uploader("Choose a DOCX file", type="docx")

if uploaded_file is not None:
    st.info("File uploaded successfully! Click the button below to process.")
    
    if st.button("Detect & Redact PII", type="primary"):
        with st.spinner("Processing document... This may take a moment."):
            # Create a temporary directory to store uploaded and output files
            with tempfile.TemporaryDirectory() as temp_dir:
                input_path = os.path.join(temp_dir, "input.docx")
                output_path = os.path.join(temp_dir, "redacted.docx")
                
                # Save uploaded file
                with open(input_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                try:
                    # 1. Extract text
                    text, segments = docx_processor.extract_text_with_positions(input_path)
                    
                    # 2. Detect PII
                    result = detect_pii(
                        text, regex_detector, ner_detector, context_detector,
                        merger, scorer, threshold
                    )
                    
                    # 3. Assign replacements
                    assign_replacements(result.entities, replacement_gen)
                    
                    # 4. Apply redactions
                    docx_processor.apply_redactions(input_path, output_path, result.entities)
                    
                    st.success(f"Processing complete! Found {len(result.entities)} PII entities.")
                    
                    # --- Display Results ---
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Summary by Type")
                        if result.entities:
                            # Count entities by type
                            type_counts = {}
                            for e in result.entities:
                                type_counts[e.entity_type.value] = type_counts.get(e.entity_type.value, 0) + 1
                                
                            df_counts = pd.DataFrame(
                                list(type_counts.items()), 
                                columns=['PII Type', 'Count']
                            ).sort_values(by='Count', ascending=False)
                            
                            st.bar_chart(df_counts.set_index('PII Type'))
                        else:
                            st.info("No PII detected.")
                            
                    with col2:
                        st.subheader("Action")
                        # Read the output file for downloading
                        with open(output_path, "rb") as f:
                            btn = st.download_button(
                                label="Download Redacted Document",
                                data=f,
                                file_name=f"redacted_{uploaded_file.name}",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                type="primary"
                            )
                        if btn:
                            st.balloons()
                            
                    # Display detailed table
                    st.subheader("Detailed Detections")
                    if result.entities:
                        details = []
                        for e in result.entities:
                            details.append({
                                "Type": e.entity_type.value,
                                "Original Text": e.text,
                                "Replacement": e.replacement,
                                "Detector": e.detector,
                                "Confidence": round(e.confidence, 3)
                            })
                        
                        st.dataframe(pd.DataFrame(details), use_container_width=True)
                        
                except Exception as e:
                    st.error(f"An error occurred during processing: {e}")
