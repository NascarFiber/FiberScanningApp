import streamlit as st
import pandas as pd
from datetime import datetime
from collections import Counter
import re

# --- Page Config ---
st.set_page_config(page_title="Fiber Inventory Dashboard v1.3", layout="wide")

# --- Initialize Session State ---
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame()
if "scan_log" not in st.session_state:
    st.session_state.scan_log = []
# Store previous metrics for deltas
if "prev_checked_in" not in st.session_state:
    st.session_state.prev_checked_in = None
if "prev_remaining_out" not in st.session_state:
    st.session_state.prev_remaining_out = None

# --- Helper: Scan Callback ---
def handle_scan():
    val = st.session_state.scan_input
    if val:
        now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        st.session_state.scan_log.insert(0, {"Cable ID": val, "Timestamp": now})
        st.session_state.scan_input = ""

# --- Sidebar Navigation ---
st.sidebar.title("🚀 Fiber Scanning App")
module = st.sidebar.radio("Choose Module:", ["Inventory", "Data Compare", "ICODE Generator"], index=0)

# --- Inventory Module ---
if module == "Inventory":
    # Sidebar controls
    grid_file = st.sidebar.file_uploader("1) Upload Inventory CSV", type=["csv"])
    st.sidebar.text_input("2) Scan to Check In", key="scan_input", on_change=handle_scan)
    search_term = st.sidebar.text_input("3) Search Inventory", key="search_term")

    # Load CSV
    if grid_file:
        try:
            st.session_state.df = pd.read_csv(grid_file)
        except Exception as e:
            st.error(f"Error loading CSV: {e}")
    df = st.session_state.df

    # Compute metrics
    total_inventory = len(df)
    scanned_codes = list({entry["Cable ID"] for entry in st.session_state.scan_log})
    checked_in = len(scanned_codes)
    remaining_out = total_inventory - checked_in

    # Header with animated metrics
    title_col, metrics_col = st.columns([3,1])
    with title_col:
        st.title("📋 Inventory & Scanning")
    with metrics_col:
        ci_delta = None if st.session_state.prev_checked_in is None else checked_in - st.session_state.prev_checked_in
        ro_delta = None if st.session_state.prev_remaining_out is None else remaining_out - st.session_state.prev_remaining_out
        st.metric("Checked In", checked_in, delta=ci_delta)
        st.metric("Remaining Out", remaining_out, delta=ro_delta)
        st.session_state.prev_checked_in = checked_in
        st.session_state.prev_remaining_out = remaining_out

    # INVENTORY DATABASE
    st.subheader("INVENTORY DATABASE")
    if df.empty:
        st.info("No inventory loaded. Upload a CSV from the sidebar.")
    else:
        disp = df.copy()
        if search_term:
            mask = disp.apply(lambda r: r.astype(str).str.contains(search_term, case=False).any(), axis=1)
            disp = disp[mask]
        st.dataframe(disp.reset_index(drop=True), use_container_width=True)
        st.download_button("Export Inventory CSV", disp.to_csv(index=False), "inventory.csv")

    # CHECK IN STATUS
    st.subheader("CHECK IN STATUS")
    if not df.empty:
        # Grouping logic
        if "Description" in df.columns:
            df["Group"] = df["Description"]
        else:
            df["Group"] = df["Cable ID"].str.extract(r"([A-Za-z]+\d+-\d+ST)", expand=False).fillna(df["Cable ID"])
        # Build status
        status_rows = []
        for g in df["Group"].unique():
            group_df = df[df["Group"] == g]
            total = len(group_df)
            out = total - sum(group_df["Cable ID"].isin(scanned_codes))
            status = "🔴" if out > 10 else ("🟡" if out > 0 else "🟢")
            status_rows.append({"Group": g, "Total": total, "Out": out, "Status": status})
        status_df = pd.DataFrame(status_rows)
        # Hide index by blanking
        status_df.index = [""] * len(status_df)
        st.dataframe(status_df, use_container_width=True)
    else:
        st.info("No data for status.")

    # Scan Log below status
    st.subheader("Scan Log")
    scan_log = pd.DataFrame(st.session_state.scan_log)
    if scan_log.empty:
        st.info("No scans yet.")
    else:
        st.dataframe(scan_log, use_container_width=True)
        st.download_button("Export Scan Log", scan_log.to_csv(index=False), "scan_log.csv")

# --- Data Compare Module ---
elif module == "Data Compare":
    st.title("🔍 Data Compare & Merge")
    left, right = st.columns([2,1])
    with left:
        st.subheader("Dataset 1")
        file1 = st.file_uploader("Upload CSV or paste below:", type=["csv"], key="file1")
        text1 = st.text_area("", key="text1", height=100)
        st.subheader("Dataset 2")
        file2 = st.file_uploader("Upload CSV or paste below:", type=["csv"], key="file2")
        text2 = st.text_area("", key="text2", height=100)
    with right:
        if st.button("Compare"):
            def load_list(f, t):
                if f:
                    return pd.read_csv(f).iloc[:,0].astype(str).tolist()
                return [l for l in t.splitlines() if l.strip()]
            lst1 = load_list(file1, text1)
            lst2 = load_list(file2, text2)
            only1 = sorted(set(lst1) - set(lst2))
            only2 = sorted(set(lst2) - set(lst1))
            common = sorted(set(lst1) & set(lst2))
            st.subheader("Only in 1")
            st.text_area("", "\n".join(only1), height=80)
            st.subheader("Common")
            st.text_area("", "\n".join(common), height=80)
            st.subheader("Only in 2")
            st.text_area("", "\n".join(only2), height=80)
        if st.button("Merge Lists"):
            def load_list(f, t):
                if f:
                    return pd.read_csv(f).iloc[:,0].astype(str).tolist()
                return [l for l in t.splitlines() if l.strip()]
            lst1 = load_list(file1, text1)
            lst2 = load_list(file2, text2)
            merged = sorted(set(lst1) | set(lst2))
            st.subheader("Merged Output")
            st.text_area("", "\n".join(merged), height=200)

# --- ICODE Generator Module ---
elif module == "ICODE Generator":
    st.title("🛠️ ICODE Generator")
    barcodes_input = st.text_area("Enter barcodes (one per line)")
    if st.button("Generate ICODEs"):
        barcodes = [b.strip() for b in barcodes_input.splitlines() if b.strip()]
        icodes = []
        for bc in barcodes:
            m = re.match(r"([A-Za-z]+)(\d+)-?\d*([A-Za-z]+)(\d+)", bc)
            if m:
                owner, length, connector, _ = m.groups()
                icode = f"{connector}{owner}{length}"
            else:
                icode = "ERROR"
            icodes.append(icode)
        df_ic = pd.DataFrame({"Barcode": barcodes, "ICODE": icodes})
        st.dataframe(df_ic, use_container_width=True)
        counts = Counter(icodes)
        unique = [f"**{ic}**" if counts[ic]>1 else ic for ic in counts]
        st.subheader("Unique ICODEs")
        st.markdown("\n".join(unique))
