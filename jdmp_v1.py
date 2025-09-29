import streamlit as st
import pandas as pd

st.title("JDMP Prototype: Importing, Cleaning, Validation")

# --- upload files ---
urns_file = st.file_uploader("Upload URNs Excel", type=["xlsx"])
desc_file = st.file_uploader("Upload Descriptive Metadata Excel", type=["xlsx"])

# --- URNs file handling ---
if urns_file:
    urns_df = pd.read_excel(urns_file)

    # drop rows with NaN or blank FILE-URN
    if "FILE-URN" in urns_df.columns:
        urns_df = urns_df.dropna(subset=["FILE-URN"])
        urns_df = urns_df[urns_df["FILE-URN"].astype(str).str.strip() != ""]
        st.success(f"Cleaned URNs: {len(urns_df)} rows remaining")
    else:
        st.error("Column 'FILE-URN' not found in URNs file")

    urns_cols = urns_df.columns.tolist()
    st.subheader("Original URNs Columns")

    # select the match field (default = OBJ-OSN)
    urns_default_key_col = "OBJ-OSN"
    if urns_default_key_col in urns_cols:
        urns_default_key_index = urns_cols.index(urns_default_key_col)
    else:
        urns_default_key_index = 0
    urns_key_col = st.selectbox("Select the match field", urns_cols, index=urns_default_key_index)

# --- descriptive metadata file handling ---
if desc_file:
    desc_df = pd.read_excel(desc_file)
    desc_cols = desc_df.columns.tolist()
    st.subheader("Descriptive Metadata Columns")

    # select columns
    desc_key_col = st.selectbox("Select the match field", desc_cols, index=1)  # default: 2nd column
    desc_title_col = st.selectbox("Select the Title column", desc_cols)
    desc_start_date_col = st.selectbox("Select the Start Date column", desc_cols)
    desc_end_date_col = st.selectbox("Select the End Date column", desc_cols)

# --- validation ---
if urns_file and desc_file:
    if "urns_key_col" in locals() and "desc_key_col" in locals():
        urn_keys = set(urns_df[urns_key_col].astype(str).str.strip())
        desc_keys = set(desc_df[desc_key_col].astype(str).str.strip())

        # check row count
        if len(urns_df) != len(desc_df):
            st.warning(f"Row count mismatch! URNs: {len(urns_df)}, Descriptive Metadata: {len(desc_df)}")

        # check key sets
        desc_missing_keys = urn_keys - desc_keys
        urns_missing_keys = desc_keys - urn_keys

        if desc_missing_keys or urns_missing_keys:
            st.warning("Key mismatch detected!")
            if desc_missing_keys:
                st.write(f"URNs not in Descriptive Metadata: {list(desc_missing_keys)}")
            if urns_missing_keys:
                st.write(f"Descriptive Metadata not in URNs: {list(urns_missing_keys)}")

        # allow override (TBD)
        #override = st.checkbox("Override mismatch warning and proceed")
        #if override:
        #    st.success("Override enabled: You can proceed to populate the template.")

    else:
        st.info("Please select the key columns for validation to run.")




