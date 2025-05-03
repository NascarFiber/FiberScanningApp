import streamlit as st
import pandas as pd
from datetime import datetime
from collections import Counter
import re

# --- Page Config ---
st.set_page_config(page_title="Fiber Inventory Dashboard", layout="wide")

# --- Sidebar Navigation ---
st.sidebar.title("🚀 Fiber Scanning App")
module = st.sidebar.radio(
    "Choose Module:",
    ["Inventory", "Data Compare", "ICODE Generator"]
)

# --- Inventory Module ---
if module == "Inventory":
    st.title("📋 Inventory & Scanning")

    # Sidebar controls
    grid_file = st.sidebar.file_uploader("1) Upload Inventory CSV", type=["csv"])
    scan_input = st.sidebar.text_input("2) Scan or Enter Code", key="scan_input")

    # Initialize inventory DataFrame in session state
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame()
    if grid_file:
        try:
            st.session_state.df = pd.read_csv(grid_file)
        except Exception as e:
            st.error(f"Error loading CSV: {e}")
    df = st.session_state.df

    # Initialize scan log
    if "scan_log" not in st.session_state:
        st.session_state.scan_log = []

    # Handle new scan
    if scan_input:
        now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
        st.session_state.scan_log.insert(0, {"Cable ID": scan_input, "Timestamp": now})
        st.session_state.scan_input = ""  # clear input box
        st.experimental_rerun()

    scan_log = pd.DataFrame(st.session_state.scan_log)

    # Calculate checked-out state
    codes = [entry["Cable ID"] for entry in st.session_state.scan_log]
    cnt = Counter(codes)
    checked_out = [code for code, count in cnt.items() if count % 2 == 1]
    active_count = len(checked_out)
    total_inventory = len(df) if not df.empty else 0
    remaining = total_inventory - active_count

    # Breakdown by description
    if "Description" in df.columns:
        desc_map = df.set_index("Cable ID")["Description"].to_dict()
    else:
        desc_map = {}
    desc_out = {}
    for code in checked_out:
        desc = desc_map.get(code, "Unknown")
        desc_out.setdefault(desc, []).append(code)

    # Layout: Metrics and Breakdown
    col1, col2 = st.columns([3, 1])
    with col2:
        st.metric("Checked Out", active_count)
        st.metric("Remaining", remaining)
        st.markdown("**Out Breakdown**")
        for desc, codes in desc_out.items():
            st.write(f"- **{desc}**: {', '.join(codes)}")

    # Inventory Table & Exports
    with col1:
        st.subheader("Inventory")
        if df.empty:
            st.info("No inventory loaded. Upload a CSV from the sidebar.")
        else:
            disp = df.copy()
            disp.index = disp.index + 1  # start at 1
            st.dataframe(disp, use_container_width=True)
            st.download_button(
                "Export Inventory CSV",
                disp.to_csv(index=False),
                "inventory.csv",
                "text/csv"
            )

        st.subheader("Scan Log")
        if scan_log.empty:
            st.info("No scans yet. Use the scan box above.")
        else:
            st.dataframe(scan_log, use_container_width=True)
            st.download_button(
                "Export Scan Log",
                scan_log.to_csv(index=False),
                "scan_log.csv",
                "text/csv"
            )
            report = scan_log.copy()
            report["Checked Out"] = report["Cable ID"].isin(checked_out)
            st.download_button(
                "Download Report",
                report.to_csv(index=False),
                "report.csv",
                "text/csv"
            )

# --- Data Compare Module ---
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
            c1.subheader("Only in Dataset 1")
            c1.write(only1)
            c2.subheader("Common")
            c2.write(common)
            c3.subheader("Only in Dataset 2")
            c3.write(only2)

            st.download_button("Download Only in 1", "\n".join(only1), "only1.txt")
            st.download_button("Download Common", "\n".join(common), "common.txt")
            st.download_button("Download Only in 2", "\n".join(only2), "only2.txt")
        except Exception as e:
            st.error(f"Error processing files: {e}")

# --- ICODE Generator Module ---
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
