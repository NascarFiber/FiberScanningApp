import streamlit as st
import pandas as pd
from datetime import datetime
from collections import Counter
import re

# --- Page Config ---
st.set_page_config(page_title="Fiber Inventory Dashboard", layout="wide")

# --- Callback for scanning input ---
def handle_scan():
    code = st.session_state.scan_input.strip()
    if code:
        now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        # 1) Log the scan
        st.session_state.scan_log.insert(0, {"Cable ID": code, "Timestamp": now})
        # 2) Update the 'In Time' for that asset in inventory
        df = st.session_state.df
        if not df.empty and 'Cable ID' in df.columns:
            df.loc[df['Cable ID'] == code, 'In Time'] = now
            # re-apply 1-based index
            df.index = range(1, len(df) + 1)
            st.session_state.df = df
        # 3) Clear the scan box
        st.session_state.scan_input = ''

# --- Sidebar Navigation ---
st.sidebar.title("🚀 Fiber Scanning App")
module = st.sidebar.radio("Choose Module:", ["Inventory", "Data Compare", "ICODE Generator"])

# --- Inventory & Scanning Module ---
if module == "Inventory":
    st.title("📋 INVENTORY & SCANNING")
    # Sidebar controls
    inv_file = st.sidebar.file_uploader("1) Upload Inventory CSV", type=["csv"])
    st.sidebar.text_input("2) Scan or Enter Code", key="scan_input", on_change=handle_scan)

    # Initialize or load inventory DataFrame
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame()
    if inv_file:
        df = pd.read_csv(inv_file)
        # add the two new columns
        df["In Time"] = ""
        df["Notes"]   = ""
        # 1-based index
        df.index = range(1, len(df) + 1)
        st.session_state.df = df
    df = st.session_state.df

    # Initialize scan log
    if "scan_log" not in st.session_state:
        st.session_state.scan_log = []
    scan_log = pd.DataFrame(st.session_state.scan_log)

    # --- Metrics ---
    checked_in = df["In Time"].astype(bool).sum() if not df.empty else 0
    total      = len(df)
    remaining  = total - checked_in

    c1, c2 = st.columns(2)
    c1.metric("Checked In",     checked_in)
    c2.metric("Remaining Out", remaining)

    # --- Interactive Inventory Table ---
    st.subheader("INVENTORY DATABASE")
    if not df.empty:
        # show an editable table, with index starting at 1
        edited = st.experimental_data_editor(
            df,
            key="inv_editor",
            use_container_width=True
        )
        # commit any user edits (Notes or In Time) back into session_state
        st.session_state.df = edited
    else:
        st.info("Upload a CSV to populate the inventory table.")

    # --- Check In Status ---
    if not df.empty:
        status_df = (
            st.session_state.df
              .groupby("Description")
              .agg(
                Total=("Cable ID", "count"),
                Out=("In Time", lambda col: col.eq("").sum())
              )
              .reset_index()
        )
        status_df["Status"] = status_df["Out"].apply(
            lambda o: "Green"  if o == 0 
                      else "Yellow" if o <= 5 
                      else "Red"
        )
        status_df.index = range(1, len(status_df) + 1)  # 1-based
        st.subheader("CHECK IN STATUS")
        st.dataframe(
            status_df[["Description", "Total", "Out", "Status"]],
            use_container_width=True
        )

    # --- Scan Log ---
    st.subheader("Scan Log")
    if scan_log.empty:
        st.info("No scans yet.")
    else:
        st.dataframe(scan_log, use_container_width=True)
        st.download_button(
            "Export Scan Log",
            scan_log.to_csv(index=False),
            "scan_log.csv",
            "text/csv"
        )

# --- Data Compare Module (unchanged) ---
elif module == "Data Compare":
    st.title("🔍 Data Compare Tool")
    df1_file = st.file_uploader("Dataset 1 (CSV)", type=["csv"], key="dc1")
    df2_file = st.file_uploader("Dataset 2 (CSV)", type=["csv"], key="dc2")

    if df1_file and df2_file:
        try:
            d1 = pd.read_csv(df1_file)
            d2 = pd.read_csv(df2_file)
            set1 = set(d1.iloc[:, 0].astype(str))
            set2 = set(d2.iloc[:, 0].astype(str))
            only1 = sorted(set1 - set2)
            only2 = sorted(set2 - set1)
            common = sorted(set1 & set2)

            c1, c2, c3 = st.columns(3)
            c1.subheader("Only in Dataset 1"); c1.write(only1)
            c2.subheader("Common");           c2.write(common)
            c3.subheader("Only in Dataset 2");c3.write(only2)

            st.download_button("Download Only in 1", "\n".join(only1), "only1.txt")
            st.download_button("Download Common",       "\n".join(common), "common.txt")
            st.download_button("Download Only in 2", "\n".join(only2), "only2.txt")
        except Exception as e:
            st.error(f"Error processing files: {e}")

# --- ICODE Generator Module (unchanged) ---
elif module == "ICODE Generator":
    st.title("🛠️ ICODE Generator")
    barcodes_input = st.text_area("Enter barcodes (one per line)")
    if st.button("Generate ICODEs"):
        barcodes = [b.strip() for b in barcodes_input.splitlines() if b.strip()]
        icodes = []
        for bc in barcodes:
            m = re.match(r"([A-Za-z]+)(\d+)-?(\d*)([A-Za-z]+)(\d+)", bc)
            if m:
                owner    = m.group(1)
                length   = m.group(2)
                connector= m.group(4)
                icode    = f"{connector}{owner}{length}"
            else:
                icode = "ERROR"
            icodes.append(icode)

        df_ic = pd.DataFrame({"Barcode": barcodes, "ICODE": icodes})
        st.dataframe(df_ic, use_container_width=True)

        counts = Counter(icodes)
        unique_lines = [
            f"**{ic}**" if counts[ic] > 1 else ic
            for ic in counts
        ]
        st.subheader("Unique ICODEs")
        st.markdown("\n".join(unique_lines))
