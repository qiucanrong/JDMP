import streamlit as st
import pandas as pd
import io

st.title("JDMP Prototype")
st.header("Importing, Cleaning, Validation, Template Population (category 1, 2, 3), Exporting")

# --- upload files ---
urns_file = st.file_uploader("Upload URNs Excel", type=["xlsx"])
desc_file = st.file_uploader("Upload Descriptive Metadata Excel", type=["xlsx"])
template_file = st.file_uploader("Upload SharedShelf Template Excel (optional)", type=["xlsx"])

# --- template file handling ---
# cached function: loads template (or any Excel) file once, then reuses result
@st.cache_data
def load_template(path: str):
    return pd.read_excel(path)

if template_file: # if user uploads a new template
    try:
        template_df = pd.read_excel(template_file)
        st.success(f"Custom template loaded: {template_df.shape[1]} columns detected")
    except Exception as e:
        st.error(f"Could not read the uploaded template: {e}")
        template_df = None

else: # fallback to default stored template
    try:
        template_df = load_template("SharedShelf Template.xlsx")
        #st.info("No template uploaded. Using default SharedShelf template.")
        st.success(f"Default SharedShelf template: {template_df.shape[1]} columns detected")
    except Exception as e:
        st.error(f"Default template not found or unreadable: {e}")
        template_df = None

# --- URNs file handling ---
if urns_file:
    urns_df = pd.read_excel(urns_file)
    st.subheader("URNs")

    # drop rows with NaN or blank FILE-URN
    if "FILE-URN" in urns_df.columns:
        urns_df = urns_df.dropna(subset=["FILE-URN"]).copy()
        urns_df = urns_df[(urns_df["FILE-URN"].astype(str).str.strip() != "")].reset_index(drop=True)
        st.success(f"Cleaned URNs: {len(urns_df)} rows remaining")
    else:
        st.error("Column 'FILE-URN' not found in URNs file")

    urns_cols = urns_df.columns.tolist()

    # select the match field (default = OBJ-OSN)
    urns_default_key_col = "OBJ-OSN"
    if urns_default_key_col in urns_cols:
        urns_default_key_index = urns_cols.index(urns_default_key_col)
    else:
        urns_default_key_index = 0
    urns_key_col = st.selectbox("Select the Match Field", urns_cols, index=urns_default_key_index)

# --- descriptive metadata file handling ---
if desc_file:
    desc_df = pd.read_excel(desc_file)
    st.subheader("Descriptive Metadata")

    desc_cols = desc_df.columns.tolist()
    desc_cols_with_none = [None] + desc_cols

    # select types
    metadata_type = st.selectbox("Select Metadata Type", [None, "Posters", "Ephemera", "Memorabilia"])
    cataloging_type = st.radio("Select Cataloging Type", [ "Full Cataloging", "Provisional Records"], horizontal=True)
    geographic_type = st.selectbox("Select Geographic Type", [None, "Israel", "World Judaica"])

    # select columns
    desc_key_col = st.selectbox("Select the Match Field", desc_cols, index=1)  # default: 2nd column
    desc_title_col = st.selectbox("Select the Title Column", desc_cols_with_none)
    desc_start_date_col = st.selectbox("Select the Start Date Column", desc_cols_with_none)
    desc_end_date_col = st.selectbox("Select the End Date Column", desc_cols_with_none)

    # check if user made all required selections
    missing_selections = []
    if metadata_type is None:
        missing_selections.append("Metadata Type")
    if geographic_type is None:
        missing_selections.append("Geographic Type")
    if desc_title_col is None:
        missing_selections.append("Title Column")
    if desc_start_date_col is None:
        missing_selections.append("Start Date Column")
    if desc_end_date_col is None:
        missing_selections.append("End Date Column")
    
    # store choices in session state
    #st.session_state["metadata_type"] = metadata_type
    #st.session_state["geographic_type"] = geographic_type
    #st.session_state["cataloging_type"] = cataloging_type
    #st.session_state["desc_title_col"] = desc_title_col
    #st.session_state["desc_start_date_col"] = desc_start_date_col
    #st.session_state["desc_end_date_col"] = desc_end_date_col

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
        #    st.success("Override enabled: You can proceed to populate the template")

    else:
        st.info("Please select the match fields for validation to run.")

# --- template population pipeline ---
if urns_file and desc_file and template_df is not None:
    st.subheader("Populated SharedShelf Template")

    # initialize blank template aligned to URNs row count
    target_rows = len(urns_df)
    template_out = template_df.head(0).copy()
    template_out = template_out.reindex(range(target_rows)).reset_index(drop=True)

    # category 1: standard fixed values
    try:
        template_out.loc[:, "SSID"] = "NEW"
        template_out.loc[:, "File Count"] = 1
        template_out.loc[:, "Repository[34349]"] = "Judaica Division, Widener Library"
        template_out.loc[:, "Description[34357]"] = "(HJ WORDING TBD)"
    except KeyError as e:
        st.error(f"Template missing expected column(s) for fixed value population: {e}")

    # category 2: FILE-URN + OBJ-OSN (based on URNs file)
    try:
        template_out.loc[:, "Filename"] = "drs:" + urns_df["FILE-URN"].astype(str).str.strip()
        template_out.loc[:, "Repository Classification Number[34364]"] = urns_df["OBJ-OSN"].astype(str).str.strip()
    except KeyError as e:
        st.error(f"Template missing expected column(s) for URN-related population: {e}")

    # category 3-1: start / end dates (based on descriptive metadata)
    if desc_start_date_col is not None and desc_end_date_col is not None:
        start = pd.to_numeric(desc_df[desc_start_date_col], errors="coerce")
        end   = pd.to_numeric(desc_df[desc_end_date_col], errors="coerce")
        template_date_cols = ["Date Description[34341]", "ARTstor Earliest Date[34342]", "Latest Date[34343]",
                              "Earliest Date[2560433]", "Latest Date[2560435]"]

        def assign_dates(start, end):
            if pd.notna(start) and pd.notna(end) and (start != end):  # both present & different
                return f"{int(start)}-{int(end)}", int(start), int(end), int(start), int(end)
            elif pd.notna(start) and pd.notna(end) and (start == end):  # both present & identical
                return int(start), int(start), int(end), int(start), int(end)
            elif pd.notna(start) and pd.isna(end):  # start present, end blank
                return int(start), int(start), int(start), int(start), int(start)
            else:  # both blank
                return "", "", "", "", ""
        
        date_values = [assign_dates(s, e) for s, e in zip(start, end)]
        date_df = pd.DataFrame(date_values, columns=template_date_cols)
        for col in date_df.columns:
            try:
                template_out[col] = date_df[col]
            except KeyError as e:
                st.error(f"Template missing expected column(s) for Start/End Date Population: {e}")

    # category 3-2: title (based on descriptive metadata)
    if desc_title_col is not None and metadata_type is not None and cataloging_type is not None and cataloging_type is not None:
        if desc_title_col not in desc_df.columns:
            st.error("Selected Title column not found in descriptive metadata file.")
            #st.stop()
        
        titles = desc_df[desc_title_col].astype(str).str.strip()

        # define logic only for posters for now
        if metadata_type == "Posters":
            if cataloging_type == "Full Cataloging":
                populated_titles = titles
            elif cataloging_type == "Provisional Records":
                if geographic_type == "Israel":
                    populated_titles = "Israel Poster Collection - " + titles + " [CATALOGING IN PROCESS.]"
                elif geographic_type == "World Judaica":
                    populated_titles = "Judaica Poster Collection - " + titles + " [CATALOGING IN PROCESS.]"
                else:
                    st.warning("Geographic Type not selected; titles left blank.")
                    populated_titles = ""
            else:
                st.warning("Unknown Cataloging Type; titles left blank.")
                populated_titles = ""

        try:
            template_out.loc[:, "Title[34338]"] = populated_titles
        except KeyError as e:
            st.error(f"Template missing expected column for Title population: {e}")

    # save intermediate for future categories
    st.session_state["template_out"] = template_out

    # show combined preview of what’s been filled so far
    preview_cols = ["SSID", "Filename", "File Count", 
                    "Repository[34349]", "Description[34357]", "Repository Classification Number[34364]"]
    if "populated_titles" in locals():
        preview_cols += ["Title[34338]"]
    if "template_date_cols" in locals():
        preview_cols += template_date_cols

    st.dataframe(template_out[preview_cols].head(10), use_container_width=True)

    # export to Excel
    if missing_selections:
        st.warning(
            f"Please select value(s) for {', '.join(missing_selections)} before downloading the populated template."
        )

    else:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            template_out.to_excel(writer, index=False)
        st.download_button(
            label="Download Populated SharedShelf Template (Excel)",
            data=output.getvalue(),
            file_name="JDMP_Populated_Template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

