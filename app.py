import os
import streamlit as st
import yaml
import json

from services.file_parser import extract_text
from services.metadata_extractor import extract_metadata
from services.eln_client import list_experiments, get_eln_data
from models.metadata_models import Metadata


st.set_page_config(page_title="Scientific Metadata Extractor", page_icon="🧬", layout="centered")
st.title("🧬 Scientific Metadata Extractor")

uploaded_file = st.file_uploader("Upload scientific file")

if uploaded_file:

    with open("vocab/controlled_vocab.yaml", "r") as f:
        vocab = yaml.safe_load(f)

    # -------------------------
    # STEP 1: FILE PARSING
    # -------------------------
    with st.spinner("Parsing file..."):
        try:
            parsed = extract_text(uploaded_file)
        except Exception as e:
            st.error(f"Failed to parse file: {e}")
            st.stop()

    text = parsed["text"]
    raw = parsed["raw"]

    if not text:
        st.warning("Could not extract any content from the file.")
        st.stop()

    with st.expander("Raw file metadata"):
        st.json(raw)

    with st.expander("Content sent to AI"):
        st.text(text)

    # -------------------------
    # STEP 2: ELN LOOKUP
    # -------------------------
    st.subheader("Link to ELN Experiment")

    experiments = list_experiments()
    exp_options = {f"{e['id']} — {e['title']}": e["filename"] for e in experiments}

    selected_label = st.selectbox(
        "Select experiment",
        options=["— none —"] + list(exp_options.keys()),
        help="Link this file to an ELN experiment to pre-fill metadata.",
    )

    eln_data = None

    if selected_label != "— none —":
        eln_data = get_eln_data(exp_options[selected_label])

        exp_block = eln_data.get("experiment", {})
        meta_block = eln_data.get("metadata", {})
        sections = eln_data.get("sections", {})

        with st.expander(f"ELN — {exp_block.get('title', selected_label)}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"**ID:** {exp_block.get('id', '—')}")
                st.markdown(f"**Status:** {exp_block.get('status', '—')}")
                st.markdown(f"**Author:** {meta_block.get('author', {}).get('name', '—')}")
                st.markdown(f"**Signed:** {meta_block.get('author', {}).get('signedDate', '—')}")
            with col2:
                st.markdown(f"**Path:** {exp_block.get('path', '—')}")
                st.markdown(f"**Confidentiality:** {exp_block.get('confidentiality', '—')}")
                st.markdown(f"**Approver:** {meta_block.get('approver', {}).get('name', '—')}")
                st.markdown(f"**Approved:** {meta_block.get('approver', {}).get('signedDate', '—')}")

            background = sections.get("background", {}).get("text")
            if background:
                st.markdown("**Background**")
                st.caption(background)

            objectives = sections.get("aim", {}).get("objectives", [])
            if objectives:
                st.markdown("**Objectives**")
                for obj in objectives:
                    st.caption(f"• {obj}")

            conclusion = sections.get("conclusion", {})
            conclusion_summary = conclusion.get("summary")
            conclusion_findings = conclusion.get("keyFindings", [])
            if conclusion_summary or conclusion_findings:
                st.markdown("**Conclusion**")
                if conclusion_summary:
                    st.caption(conclusion_summary)
                for finding in conclusion_findings:
                    st.caption(f"• {finding}")

            results = sections.get("results", {})
            results_notes = results.get("notes")
            results_findings = results.get("keyFindings", [])
            if results_notes or results_findings:
                st.markdown("**Results**")
                if results_notes:
                    st.caption(results_notes)
                for finding in results_findings:
                    st.caption(f"• {finding}")

    # -------------------------
    # STEP 3: AI EXTRACTION
    # -------------------------
    with st.spinner("Extracting metadata with AI..."):
        result = extract_metadata(text, vocab, eln_data)

    metadata = result["metadata"]
    usage    = result["usage"]

    if not metadata:
        st.warning("AI extraction returned no results. You can still fill in the form manually.")
        metadata = {}

    if usage:
        st.caption(
            f"AI call — {usage['prompt_tokens']:,} prompt tokens · "
            f"{usage['completion_tokens']:,} completion tokens · "
            f"${usage['cost_usd']:.4f}"
        )

    if eln_data:
        metadata["experiment_id"] = eln_data.get("experiment", {}).get("id")

    model_fields = set(Metadata.model_fields.keys())

    # -------------------------
    # STEP 4: FORM UI
    # -------------------------
    st.subheader("Review & Edit Metadata")
    st.caption("Fields pre-filled by AI from file content and ELN experiment data.")

    edited_metadata = {}

    vocab_key_map = {
        "data_source": "Data Source",
        "data_retention": "Data Retention",
        "function": "Function",
        "file_type": "File Type",
        "modality": "Modality",
        "microscopy_type": "Microscopy Type",
        "species": "Species",
        "cell_line": "Cell Line",
        "treatment": "Treatment",
        "instrument_name": "Instrument Name",
        "marker": "Marker",
    }

    field_groups = {
        "Dataset": ["experiment_id", "data_source", "data_retention", "function", "file_type", "modality"],
        "Biology": ["species", "cell_line", "treatment", "marker"],
        "Instrumentation": ["microscopy_type", "instrument_name"],
    }

    for group_label, group_fields in field_groups.items():
        st.markdown(f"**{group_label}**")

        for field_name in group_fields:
            if field_name not in model_fields:
                continue

            current_value = metadata.get(field_name)
            label = field_name

            vocab_key = vocab_key_map.get(field_name)
            options = vocab.get(vocab_key, []) if vocab_key else []

            if field_name == "marker":
                default = ", ".join(current_value) if isinstance(current_value, list) else ""
                raw_input = st.text_input(
                    label,
                    value=default,
                    help=f"Allowed values: {', '.join(options)}" if options else None,
                )
                edited_metadata[field_name] = [x.strip() for x in raw_input.split(",") if x.strip()]

            elif options:
                display_options = ["(none)"] + options
                current_str = str(current_value) if current_value else "(none)"
                if current_str not in display_options:
                    display_options = [current_str] + display_options
                idx = display_options.index(current_str) if current_str in display_options else 0

                selected = st.selectbox(label, display_options, index=idx)
                edited_metadata[field_name] = None if selected == "(none)" else selected

            else:
                edited_metadata[field_name] = st.text_input(
                    label,
                    value=str(current_value) if current_value else "",
                )

        st.divider()


    # -------------------------
    # STEP 5: OUTPUT
    # -------------------------
    st.subheader("Final Metadata")
    st.json(edited_metadata)

    if st.button("Save Metadata", type="primary"):
        try:
            os.makedirs("output", exist_ok=True)
            with open("output/extracted_metadata.json", "w") as f:
                json.dump(edited_metadata, f, indent=2)
            st.success("Metadata saved to output/extracted_metadata.json")
        except Exception as e:
            st.error(f"Failed to save: {e}")