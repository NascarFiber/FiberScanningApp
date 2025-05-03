import streamlit as st
import pandas as pd
from datetime import datetime
import re
from collections import Counter

# --- Page Config ---
st.set_page_config(page_title="Fiber Inventory Dashboard", layout="wide")

# --- Scan callback: logs & stamps In Time ---
def handle_scan():
    code = st.session_state.scan_input.strip()
    if not code:
        return
    now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    # 1) Log the scan
    st.session_state.scan_log.insert(0, {"Cable ID": code, "Timestamp": now})
    # 2) Stamp “In Time” on the matching row
    df = st.session_state.df
    if not df.empty and "Cable ID" in df.columns:
        matches = df["Cable ID"] == code
        if matches.any():
            df.loc[matches, "In Time"] = now
            # re-index starting at 1
            df.index = range(1, len(df) + 1)
            st.session_state.df = df
    # 3) Clear the scan box
    st.session_state.scan_input = ""

# --- Sidebar nav ---
st.sidebar.title("🚀 Fiber Scanning App")
module = st.sidebar.radio("Choose Module:", ["Inventory", "Data Compare", "ICODE Generator"])

# --- INVENTORY & SCANNING MODULE ---
if module == "Inventory":
    # Header + Metrics side-by-side
    c0, c1, c2 = st.columns([4,1,1])
    c0.markdown("## 📋 INVENTORY & SCANNING")
    # Prepare metrics placeholders (will be updated below)
    checked_in_metric = c1.empty()
    remaining_metric  = c2.empty()

    # Sidebar: upload & scan
    inv_file = st.sidebar.file_uploader("1) Upload Inventory CSV", type=["csv"])
    st.sidebar.text_input(
        "2) Scan or Enter Code",
        key="scan_input",
        on_change=handle_scan,
        placeholder="Type or scan then Enter"
    )

    # Load or initialize DataFrame
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame()
    if inv_file:
        df = pd.read_csv(inv_file)
        df["In Time"] = ""
        df["Notes"]   = ""
        df.index      = range(1, len(df) + 1)
        st.session_state.df = df
    df = st.session_state.df

    # Initialize scan log
    if "scan_log" not in st.session_state:
        st.session_state.scan_log = []
    scan_log = pd.DataFrame(st.session_state.scan_log)

    # Editable inventory table
    st.subheader("INVENTORY DATABASE")
    if df.empty:
        st.info("Upload a CSV to populate the inventory.")
    else:
        edited = st.data_editor(
            df,
            key="inv_editor",
            hide_index=False,
            use_container_width=True
        )
        # Commit edits (Notes or manual In Time)
        st.session_state.df = edited
        df = edited

        # Recalculate and display metrics
        total      = len(df)
        checked_in = df["In Time"].astype(bool).sum()
        remaining  = total - checked_in
        checked_in_metric.metric("Checked In", checked_in)
        remaining_metric.metric("Remaining Out", remaining)

        # Build and show status table
        status = (
            df.groupby("Description")
              .agg(
                Total=("Cable ID","count"),
                Out=("In Time", lambda col: col.eq("").sum())
              )
              .reset_index()
        )
        status["Status"] = status["Out"].apply(
            lambda o: "🟢" if o == 0 else ("🟡" if o <= 5 else "🔴")
        )
        st.subheader("CHECK IN STATUS")
        st.dataframe(
            status[["Description","Total","Out","Status"]],
            hide_index=True,
            use_container_width=True
        )

    # Scan log at bottom
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

# --- DATA COMPARE MODULE (unchanged) ---
elif module == "Data Compare":
    st.title("🔍 Data Compare Tool")
    df1 = st.file_uploader("Dataset 1 (CSV)", type=["csv"], key="dc1")
    df2 = st.file_uploader("Dataset 2 (CSV)", type=["csv"], key="dc2")
    if df1 and df2:
        d1 = pd.read_csv(df1); d2 = pd.read_csv(df2)
        s1,set2 = set(d1.iloc[:,0].astype(str)), set(d2.iloc[:,0].astype(str))
        only1 = sorted(s1 - set2); only2 = sorted(set2 - s1); common = sorted(s1 & set2)
        c1,c2,c3 = st.columns(3)
        c1.subheader("Only in 1"); c1.write(only1)
        c2.subheader("Common");      c2.write(common)
        c3.subheader("Only in 2"); c3.write(only2)
        st.download_button("Download Only in 1", "\n".join(only1),"only1.txt")
        st.download_button("Download Common",     "\n".join(common),"common.txt")
        st.download_button("Download Only in 2", "\n".join(only2),"only2.txt")

# --- ICODE GENERATOR MODULE (unchanged) ---
elif module == "ICODE Generator":
    st.title("🛠️ ICODE Generator")
    bc_input = st.text_area("Enter barcodes (one per line)")
    if st.button("Generate ICODEs"):
        lines = [l.strip() for l in bc_input.splitlines() if l.strip()]
        ics = []
        for bc in lines:
            m = re.match(r"([A-Za-z]+)(\d+)-?(\d*)([A-Za-z]+)(\d+)", bc)
            ics.append(f"{m.group(4)}{m.group(1)}{m.group(2)}" if m else "ERROR")
        df_ic = pd.DataFrame({"Barcode": lines, "ICODE": ics})
        st.dataframe(df_ic, use_container_width=True)
        cnt = Counter(ics)
        uniques = [f"**{i}**" if cnt[i]>1 else i for i in cnt]
        st.subheader("Unique ICODEs")
        st.markdown("\n".join(uniques))
