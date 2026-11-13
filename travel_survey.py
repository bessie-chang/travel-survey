import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="員工國外旅遊意願調查", page_icon="✈️", layout="centered")

DESTINATIONS = ["日本－四國", "越南－峴港", "馬來西亞－馬六甲"]

@st.cache_resource
def get_worksheet():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_url(st.secrets["sheet_url"]).sheet1
    return sheet

sheet = get_worksheet()

tab1, tab2 = st.tabs(["📝 填寫調查表", "📊 統計結果 (主辦人專用)"])

with tab1:
    st.title("✈️ 年度員工國外旅遊意願調查")
    st.info(
        "各位同仁大家好：\n\n"
        "為了規劃最符合大家期待的國外行程，請協助填寫本調查表。\n"
        "※ 系統將依「順位積分加總」決定最終成行地點，請依實際可配合出發的意願排序！"
    )

    st.subheader("一、基本資料")
    col1, col2 = st.columns(2)
    with col1:
        dept = st.selectbox("所屬部門 *", ["管理部", "財務會計部", "業務部", "行銷企劃部", "研發技術部", "生產製造部", "其他"])
        emp_id = st.text_input("員工編號 *")
    with col2:
        name = st.text_input("真實姓名（保險與機票核對用） *")
        intent = st.radio("本次國外旅遊參加意願 *", ["參加（僅本人）", "參加（攜伴／眷屬同行）", "不克參加"])

    total_people = 0
    rank1, rank2, rank3 = "", "", ""
    travel_month = []
    passport_status = ""
    notes = ""

    if intent != "不克參加":
        st.divider()
        st.subheader("二、人數與行程志願排序")

        if intent == "參加（攜伴／眷屬同行）":
            total_people = st.number_input("包含您本人，預計總參加人數：", min_value=2, max_value=10, value=2, step=1)
        else:
            total_people = 1

        st.markdown("**請依喜好程度排列您想去的行程順位（不可重複選擇）：**")
        c1, c2, c3 = st.columns(3)
        with c1:
            rank1 = st.selectbox("🥇 第 1 志願（最想去）*", DESTINATIONS, index=0)
        with c2:
            rank2 = st.selectbox("🥈 第 2 志願（次想去）*", DESTINATIONS, index=1)
        with c3:
            rank3 = st.selectbox("🥉 第 3 志願（最後考量）*", DESTINATIONS, index=2)

        st.divider()
        st.subheader("三、出發時間與證件確認")
        travel_month = st.multiselect(
            "期望出發的月份（可複選）*",
            ["2027年 3月", "2027年 4月", "2027年 5月", "2027年 6月", "2027年 9月", "2027年 10月"],
            default=["2027年 4月"]
        )
        passport_status = st.radio(
            "個人護照效期狀態（出國須有 6 個月以上效期）*",
            ["護照效期充足（6個月以上）", "護照已過期／即將到期（需重辦）", "尚未辦理過護照"]
        )
        notes = st.text_area("備註事項（若有攜伴請簡述眷屬關係與年齡，如：配偶1位、小孩5歲1位）")

    st.divider()
    if st.button("🚀 送出問卷", type="primary", use_container_width=True):
        if not name.strip() or not emp_id.strip():
            st.error("⚠️ 請填寫「姓名」與「員工編號」後再送出！")
        elif intent != "不克參加" and len({rank1, rank2, rank3}) < 3:
            st.error("⚠️ 行程志願排序不可重複，請確認第 1、2、3 志願皆為不同地點！")
        elif intent != "不克參加" and not travel_month:
            st.error("⚠️ 請至少選擇一個期望出發的月份！")
        else:
            with st.spinner("資料傳送中，請稍候..."):
                records = sheet.get_all_records()
                df_existing = pd.DataFrame(records)

                new_row = pd.DataFrame([{
                    "填寫時間": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "部門": dept,
                    "姓名": name.strip(),
                    "工號": emp_id.strip().upper(),
                    "參加意願": intent,
                    "總人數": total_people,
                    "第一志願(3分)": rank1,
                    "第二志願(2分)": rank2,
                    "第三志願(1分)": rank3,
                    "期望出發月份": ", ".join(travel_month) if travel_month else "",
                    "護照效期狀態": passport_status,
                    "備註與眷屬資訊": notes.strip()
                }])

                if not df_existing.empty and "工號" in df_existing.columns:
                    df_existing = df_existing[df_existing["工號"].astype(str) != emp_id.strip().upper()]
                df_updated = pd.concat([df_existing, new_row], ignore_index=True).fillna("")

                sheet.clear()
                sheet.update([df_updated.columns.values.tolist()] + df_updated.values.tolist())

            st.success(f"✅ 感謝 {name} 的填寫！您的資料已成功儲存（若重複填寫將自動以最新紀錄為準）。")
            st.balloons()

with tab2:
    st.subheader("📊 即時統計看板")
    password = st.text_input("請輸入管理員密碼檢視統計結果（預設密碼：8888）", type="password")

    if password == "8888":
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        if df.empty:
            st.warning("目前尚無任何填答紀錄。")
        else:
            join_df = df[df["參加意願"] != "不克參加"]
            m1, m2, m3 = st.columns(3)
            m1.metric("已填寫人數", f"{len(df)} 人")
            m2.metric("預計參加員工", f"{len(join_df)} 人")
            m3.metric("含眷屬總人數", f"{int(pd.to_numeric(join_df['總人數']).sum())} 人")

            st.markdown("### 🏆 旅遊地點順位積分排行")
            scores = {dest: {"第一志願票數": 0, "第二志願票數": 0, "第三志願票數": 0, "總積分": 0} for dest in DESTINATIONS}

            for _, row in join_df.iterrows():
                if row["第一志願(3分)"] in scores:
                    scores[row["第一志願(3分)"]]["第一志願票數"] += 1
                    scores[row["第一志願(3分)"]]["總積分"] += 3
                if row["第二志願(2分)"] in scores:
                    scores[row["第二志願(2分)"]]["第二志願票數"] += 1
                    scores[row["第二志願(2分)"]]["總積分"] += 2
                if row["第三志願(1分)"] in scores:
                    scores[row["第三志願(1分)"]]["第三志願票數"] += 1
                    scores[row["第三志願(1分)"]]["總積分"] += 1

            score_df = pd.DataFrame.from_dict(scores, orient="index").sort_values(by=["總積分", "第一志願票數"], ascending=False)
            st.dataframe(score_df, use_container_width=True)
            st.markdown("### 📋 完整填答明細")
            st.dataframe(df, use_container_width=True)