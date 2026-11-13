import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="2027 員工國外旅遊意願調查", page_icon="✈️", layout="centered")

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
    st.title("✈️ 2027 年度員工國外旅遊意願調查")
    st.info(
        "各位同仁大家好：\n\n"
        "**2027 年員工旅遊預計於 4 月中下旬舉辦**，為了規劃最符合大家期待的國外行程，請協助填寫本調查表！\n\n"
        "📌 **費用補助說明：**\n"
        "• **員工本人**：團費金額**公司補助 50%**，其餘 50% 由員工自行負擔（未滿一年者參團需簽定同意書，切結離職現金返還團費補助）。\n"
        "• **攜伴／眷屬**：團費由員工**全額自付**。"
    )

    st.subheader("一、基本資料與參加意願")
    col1, col2 = st.columns(2)
    with col1:
        dept = st.selectbox("所屬部門 *", ["管理部", "財務會計部", "業務部", "行銷企劃部", "研發技術部", "生產製造部", "其他"])
        emp_id = st.text_input("員工編號 *")
    with col2:
        name = st.text_input("真實姓名（保險與機票核對用） *")

    intent = st.radio(
        "1. 2027 年員工旅遊預計於 4 月中下旬舉辦，是否有意願參加？ *",
        [
            "是，超級期待！（僅本人參加）",
            "是，超級期待！（攜伴／眷屬同行）",
            "忍痛不參加，由我來堅守工作崗位，希望大家玩得愉快"
        ]
    )

    total_people = 0
    selected_dests = []
    travel_month = []
    passport_status = ""
    notes = ""

    # 只要選擇「是，超級期待！」才展開後續題目
    if intent.startswith("是，超級期待"):
        st.divider()
        st.subheader("二、參加人數與精選行程地點")

        if "攜伴" in intent:
            total_people = st.number_input("包含您本人，預計總參加人數（眷屬團費全額自付）：", min_value=2, max_value=10, value=2, step=1)
        else:
            total_people = 1

        st.markdown("**2. 精選行程中，您最想去哪些地點？（可複選，最少 1 個、最多 3 個）***")
        selected_dests = [dest for dest in DESTINATIONS if st.checkbox(dest, key=dest)]

        st.divider()
        st.subheader("三、出發時段與證件確認")
        travel_month = st.multiselect(
            "3. 針對 2027 年 4 月中下旬，您期望的出發時段（可複選）*",
            ["2027年 4月中旬（4/11～4/20）", "2027年 4月下旬（4/21～4/30）", "4月中下旬皆可配合", "其他月份建議（請於備註說明）"],
            default=["4月中下旬皆可配合"]
        )
        passport_status = st.radio(
            "4. 個人護照效期狀態（出國須有 6 個月以上效期）*",
            ["護照效期充足（2027年10月以後到期）", "護照已過期／即將到期（需重辦）", "尚未辦理過護照"]
        )
        notes = st.text_area("5. 備註事項（若有攜伴請簡述眷屬關係與年齡，如：配偶1位、小孩5歲1位）")

    st.divider()
    if st.button("🚀 送出問卷", type="primary", use_container_width=True):
        if not name.strip() or not emp_id.strip():
            st.error("⚠️ 請填寫「姓名」與「員工編號」後再送出！")
        elif intent.startswith("是，超級期待") and len(selected_dests) == 0:
            st.error("⚠️ 請至少勾選「1 個」您想去的旅遊地點！")
        elif intent.startswith("是，超級期待") and not travel_month:
            st.error("⚠️ 請至少選擇一個期望出發的時段！")
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
                    "感興趣的旅遊地點": ", ".join(selected_dests) if selected_dests else "",
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
            join_df = df[df["參加意願"].astype(str).str.startswith("是，超級期待")]
            m1, m2, m3 = st.columns(3)
            m1.metric("已填寫人數", f"{len(df)} 人")
            m2.metric("預計參加員工", f"{len(join_df)} 人")
            m3.metric("含眷屬總人數", f"{int(pd.to_numeric(join_df['總人數']).sum())} 人")

            st.markdown("### 🏆 旅遊地點得票數排行")
            vote_counts = {dest: {"員工得票數": 0, "含眷屬總人頭數": 0} for dest in DESTINATIONS}

            for _, row in join_df.iterrows():
                chosen = str(row["感興趣的旅遊地點"]).split(", ")
                people = int(row["總人數"]) if str(row["總人數"]).isdigit() else 1
                for dest in DESTINATIONS:
                    if dest in chosen:
                        vote_counts[dest]["員工得票數"] += 1
                        vote_counts[dest]["含眷屬總人頭數"] += people

            vote_df = pd.DataFrame.from_dict(vote_counts, orient="index").sort_values(by=["員工得票數", "含眷屬總人頭數"], ascending=False)
            st.dataframe(vote_df, use_container_width=True)

            st.markdown("### 📋 完整填答明細")
            st.dataframe(df, use_container_width=True)