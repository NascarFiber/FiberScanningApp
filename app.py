import streamlit as st
import pandas as pd
from datetime import datetime
import re
from collections import Counter

# --- Page Config ---
st.set_page_config(page_title="Fiber Inventory Dashboard", layout="wide")

# --- Scan callback ---
def handle_scan():
    code = st.session_state.scan_input.strip()
    if not code:
        return
    now = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
    # 1) Log the scan
    st.session_state.scan_log.insert(0, {"Cable ID": code, "Timestamp": now})
    # 2) Stamp In Time in the inventory table
    df = st.session_state.df
    if not df.empty and "Cable ID" in df.columns:
        mask = df["Cable ID"] == code
        df.loc[mask, "In Time"] = now
        # re-apply 1-based index
        df.index = range(1, len(df) + 1)
        st.session_state.df = df
    # 3) Clear the scan box
    st.session_state.scan_input = ""

# --- Sidebar navigation ---
st.sidebar.title("🚀 Fiber Scanning App")
module = st.sidebar.radio("Choose Module:", ["Inventory", "Data Compare", "ICODE Generator"])

# --- 1) INVENTORY & SCANNING ---
if module == "Inventory":
    st.title("📋 INVENTORY & SCANNING")

    # Sidebar: Upload + Scan input
    inv_file = st.sidebar.file_uploader("1) Upload Inventory CSV", type=["csv"])
    st.sidebar.text_input(
        "2) Scan or Enter Code",
        key="scan_input",
        on_change=handle_scan,
        placeholder="Type or scan then Enter"
    )

    # Initialize or load DataFrame
    if "df" not in st.session_state:
        st.session_state.df = pd.DataFrame()
    if inv_file:
        df = pd.read_csv(inv_file)
        # add new columns
        df["In Time"] = ""
        df["Notes"]   = ""
        # set 1-based index
        df.index = range(1, len(df) + 1)
        st.session_state.df = df
    df = st.session_state.df

    # Initialize scan log
    if "scan_log" not in st.session_state:
        st.session_state.scan_log = []
    scan_log = pd.DataFrame(st.session_state.scan_log)

    # -- Editable Inventory Table --
    st.subheader("INVENTORY DATABASE")
    if df.empty:
        st.info("Upload a CSV to populate the inventory table.")
    else:
        edited = st.data_editor(
            df,
            key="inv_editor",
            use_container_width=True,
            hide_index=False  # keep the 1-based index visible
        )
        # Commit any edits back into session
        st.session_state.df = edited
        df = edited

        # -- Metrics (recalc after table edits) --
        total      = len(df)
        checked_in = df["In Time"].astype(bool).sum()
        remaining  = total - checked_in

        c1, c2 = st.columns(2)
        c1.metric("Checked In", checked_in)
        c2.metric("Remaining Out", remaining)

        # -- Check In Status with emoji indicators --
        status_df = (
            df
              .groupby("Description")
              .agg(
                 Total=("Cable ID", "count"),
                 Out=("In Time", lambda col: col.eq("").sum())
              )
              .reset_index()
        )
        # convert to emoji traffic lights
        status_df["Status"] = status_df["Out"].apply(
            lambda o: "🟢" if o == 0 else ("🟡" if o <= 5 else "🔴")
        )
        st.subheader("CHECK IN STATUS")
        st.dataframe(
            status_df[["Description", "Total", "Out", "Status"]],
            use_container_width=True,
            hide_index=True   # hides the auto-index column
        )

    # -- Scan Log --
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

# --- 2) Data Compare (unchanged) ---
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
            c1.subheader("Only in Dataset 1");  c1.write(only1)
            c2.subheader("Common");            c2.write(common)
            c3.subheader("Only in Dataset 2");  c3.write(only2)

            st.download_button("Download Only in 1", "\n".join(only1), "only1.txt")
            st.download_button("Download Common",      "\n".join(common), "common.txt")
            st.download_button("Download Only in 2", "\n".join(only2), "only2.txt")
        except Exception as e:
            st.error(f"Error processing files: {e}")

# --- 3) ICODE Generator (unchanged) ---
elif module == "ICODE Generator":
    st.title("🛠️ ICODE Generator")
    barcodes_input = st.text_area("Enter barcodes (one per line)")
    if st.button("Generate ICODEs"):
        barcodes = [b.strip() for b in barcodes_input.splitlines() if b.strip()]
        icodes = []
        for bc in barcodes:
            m = re.match(r"([A-Za-z]+)(\d+)-?(\d*)([A-Za-z]+)(\d+)", bc)
            if m:
                owner     = m.group(1)
                length    = m.group(2)
                connector = m.group(4)
                ic = f"{connector}{owner}{length}"
            else:
                ic = "ERROR"
            icodes.append(ic)

        df_ic = pd.DataFrame({"Barcode": barcodes, "ICODE": icodes})
        st.dataframe(df_ic, use_container_width=True)

        counts = Counter(icodes)
        unique_lines = [
            f"**{ic}**" if counts[ic] > 1 else ic
            for ic in counts
        ]
        st.subheader("Unique ICODEs")
        st.markdown("\n".join(unique_lines))
