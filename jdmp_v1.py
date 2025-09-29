import streamlit as st
import pandas as pd
import io

st.title("JDMP Prototype" \
"Importing, Cleaning, Validation, Template (standard values)")

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
        st.info("Please select the match fields for validation to run.")

# --- template category 1: auto-populate standard values ---
if urns_file and desc_file and template_df:
    #st.subheader("Category 1: Populate standard template fields")

    target_rows = len(urns_df)

    # create an empty copy of the template with the correct number of rows preserved
    template_out = template_df.head(0).copy()
    template_out = template_out.reindex(range(target_rows)).reset_index(drop=True)

    # verify the SSID, Repository[34349], Description[34357] columns
    required_cols = ["SSID", "Repository[34349]", "Description[34357]"]
    missing = [c for c in required_cols if c not in template_out.columns]
    if missing:
        st.error(
            "The uploaded template is missing required columns: "
            + ", ".join(missing)
        )
    else:
        template_out.loc[:, "SSID"] = "NEW"
        template_out.loc[:, "Repository[34349]"] = "Judaica Division, Widener Library"
        template_out.loc[:, "Description[34357]"] = "(HJ WORDING TBD)"

        st.session_state["template_out"] = template_out
        st.session_state["target_rows"] = target_rows

        st.success("Category 1 complete: SSID, Repository, and Description populated for all rows.")

        st.dataframe(
            template_out[["SSID", "Repository[34349]", "Description[34357]"]].head(10),
            use_container_width=True
        )
    
    # download the updated template as Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            template_out.to_excel(writer, index=False)
        st.download_button(
            label="Download Populated SharedShelf Template (Excel)",
            data=output.getvalue(),
            file_name="JDMP_Populated_Template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )


