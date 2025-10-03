import streamlit as st
import pandas as pd
import io

st.title("JDMP Prototype")
st.header("Importing, Cleaning, Validation, Template Population (category 1, 2), Exporting")

# --- upload files ---
urns_file = st.file_uploader("Upload URNs Excel", type=["xlsx"])
desc_file = st.file_uploader("Upload Descriptive Metadata Excel", type=["xlsx"])
template_file = st.file_uploader("Upload SharedShelf Template Excel", type=["xlsx"])

# --- template file handling ---
template_df = None
if template_file:
    try:
        template_df = pd.read_excel(template_file)
        st.success(f"Template loaded: {template_df.shape[1]} columns detected")
    except Exception as e:
        st.error(f"Could not read the SharedShelf template: {e}")

# --- URNs file handling ---
if urns_file:
    urns_df = pd.read_excel(urns_file)

    # drop rows with NaN or blank FILE-URN
    if "FILE-URN" in urns_df.columns:
        urns_clean = urns_df.dropna(subset=["FILE-URN"]).copy()
        urns_clean = urns_clean[(urns_clean["FILE-URN"].astype(str).str.strip() != "")]
        st.success(f"Cleaned URNs: {len(urns_clean)} rows remaining")
    else:
        st.error("Column 'FILE-URN' not found in URNs file")

    st.subheader("Preview: Cleaned URNs Data")
    st.dataframe(urns_clean.head(20), use_container_width=True)

    urns_cols = urns_clean.columns.tolist()
    st.subheader("URNs Columns")

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
        urn_keys = set(urns_clean[urns_key_col].astype(str).str.strip())
        desc_keys = set(desc_df[desc_key_col].astype(str).str.strip())

        # check row count
        if len(urns_clean) != len(desc_df):
            st.warning(f"Row count mismatch! URNs: {len(urns_clean)}, Descriptive Metadata: {len(desc_df)}")

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
        st.info("Please select the match fields for validation to run.")

# --- template population pipeline ---
if urns_file and desc_file and template_df is not None:
    st.subheader("Populate SharedShelf Template")

    # initialize blank template aligned to URNs row count
    target_rows = len(urns_clean)
    template_out = template_df.head(0).copy()
    template_out = template_out.reindex(range(target_rows)).reset_index(drop=True)

    # category 1: standard fixed values
    try:
        template_out.loc[:, "SSID"] = "NEW"
        template_out.loc[:, "File Count"] = 1
        template_out.loc[:, "Repository[34349]"] = "Judaica Division, Widener Library"
        template_out.loc[:, "Description[34357]"] = "(HJ WORDING TBD)"
    except KeyError as e:
        st.error(f"Template missing expected column for Category 1: {e}")

    # category 2: FILE-URN + OBJ-OSN (from URNs file)
    try:
        template_out.loc[:, "Filename"] = "drs:" + urns_clean["FILE-URN"].astype(str).str.strip()
        template_out.loc[:, "Repository Classification Number[34364]"] = urns_clean["OBJ-OSN"].astype(str).str.strip()
    except KeyError as e:
        st.error(f"Template missing expected column for Category 2: {e}")

    # save intermediate for future categories
    st.session_state["template_out"] = template_out

    # show combined preview of what’s been filled so far
    preview_cols = ["SSID", "Filename", "File Count", "Repository[34349]", "Description[34357]", "Repository Classification Number[34364]"]
    st.dataframe(template_out[preview_cols].head(10), use_container_width=True)

    # export to Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        template_out.to_excel(writer, index=False)
    st.download_button(
        label="Download Populated SharedShelf Template (Excel)",
        data=output.getvalue(),
        file_name="JDMP_Populated_Template.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

