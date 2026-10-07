import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import json
import pandas as pd

# 初始化 Session State
if "questions" not in st.session_state:
    st.session_state.questions = []
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "wrong_bank" not in st.session_state:
    st.session_state.wrong_bank = []
if "show_explanation" not in st.session_state:
    st.session_state.show_explanation = False

st.set_page_config(page_title="我的 AI 刷題系統", page_icon="📝", layout="centered")
st.title("📝 我的 AI 專屬刷題系統")

# 側邊欄設定
with st.sidebar:
    st.header("⚙️ 系統設定")
    api_key = st.text_input("請輸入您的 Gemini API Key", type="password")
    
    st.divider()
    st.subheader("📥 選擇題目匯入方式")
    input_method = st.radio("您想要怎麼給 AI 題目？", ["直接貼上文字 (最穩定✨)", "上傳 PDF (可能會有亂碼)"])
    
    if st.button("清空錯題本"):
        st.session_state.wrong_bank = []
        st.success("錯題本已清空！")

# 準備要交給 AI 的純文字
raw_text_for_ai = ""

# 根據使用者的選擇顯示對應的輸入框
if input_method == "上傳 PDF":
    uploaded_file = st.file_uploader("請上傳 PDF 考古題", type="pdf")
    if uploaded_file:
        reader = PdfReader(uploaded_file)
        raw_text_for_ai = "".join([page.extract_text() for page in reader.pages])
        # 這是新增的「透視眼」功能！
        with st.expander("👀 點我檢查系統從 PDF 讀到了什麼文字？(如果是亂碼代表 PDF 加密或編碼特殊)"):
            st.text(raw_text_for_ai[:1000] + "...\n(以下省略)")

elif input_method == "直接貼上文字 (最穩定✨)":
    raw_text_for_ai = st.text_area("請在電腦上反白複製您的題目，並貼在下方框框中：", height=200)

# 當有文字也有 API Key 時，顯示開始解析按鈕
if raw_text_for_ai and api_key:
    if st.button("🚀 開始請 AI 整理選擇題"):
        with st.spinner("AI 正在努力整理題目與撰寫解析中，請耐心稍候..."):
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(
                    model_name="gemini-3.8-flash",
                    generation_config={"response_mime_type": "application/json"}
                )
                
                # 提示詞有稍微放寬標準，讓 AI 更好抓題
                prompt = f"""
                你是一個專業的考試導師。請從以下文字中，找出所有的選擇題。
                請將這些題目轉換為以下的 JSON 陣列格式。
                (注意：如果來源的選項是 1234 或 ABCD，請統一轉換為帶有 A. B. C. D. 前綴的選項)
                [
                  {{
                    "question": "題目內容",
                    "options": ["A. 選項內容", "B. 選項內容", "C. 選項內容", "D. 選項內容"],
                    "answer": "正確答案的完整文字 (必須完全等於 options 裡的其中一項)",
                    "explanation": "請簡潔說明正確答案為何正確即可。"
                  }}
                ]
                以下是題目文字：
                {raw_text_for_ai[:30000]} 
                """
                
                response = model.generate_content(prompt)
                
                st.session_state.questions = json.loads(response.text)
                st.session_state.current_index = 0
                st.session_state.show_explanation = False
                
                if len(st.session_state.questions) > 0:
                    st.success(f"解析完成！共成功整理了 {len(st.session_state.questions)} 題。")
                else:
                    st.warning("AI 找不到符合格式的選擇題，請檢查您貼上的文字是否包含清楚的題目與選項！")
                
            except Exception as e:
                st.error(f"解析失敗，請確認 API Key 是否正確。錯誤訊息: {e}")

# 主要刷題介面
if st.session_state.questions:
    current_q = st.session_state.questions[st.session_state.current_index]
    st.divider()
    st.subheader(f"第 {st.session_state.current_index + 1} 題 / 共 {len(st.session_state.questions)} 題")
    st.markdown(f"**{current_q['question']}**")
    
    user_choice = st.radio("請選擇答案：", current_q['options'], index=None, key=f"q_{st.session_state.current_index}")
    
    if st.button("送出答案"):
        if user_choice:
            st.session_state.show_explanation = True
            if user_choice == current_q['answer']:
                st.success("🎉 答對了！")
            else:
                st.error("❌ 答錯了！已自動加入錯題本。")
                if current_q not in st.session_state.wrong_bank:
                    st.session_state.wrong_bank.append(current_q)
        else:
            st.warning("請先選擇一個答案喔！")
            
    if st.session_state.show_explanation:
        st.info(f"**正確答案：** {current_q['answer']}\n\n**🔍 解析：**\n{current_q['explanation']}")
        
        if st.session_state.current_index < len(st.session_state.questions) - 1:
            if st.button("下一題 ➡️"):
                st.session_state.current_index += 1
                st.session_state.show_explanation = False
                st.rerun()
        else:
            st.balloons()
            st.success("恭喜您！已完成所有題目！")

# 錯題本區域
if st.session_state.wrong_bank:
    st.divider()
    st.subheader("📚 我的錯題收藏區")
    
    df_wrong = pd.DataFrame(st.session_state.wrong_bank)
    st.dataframe(df_wrong[['question', 'answer', 'explanation']], hide_index=True)
    
    csv = df_wrong.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下載錯題本 (CSV格式)",
        data=csv,
        file_name='my_wrong_questions.csv',
        mime='text/csv',
    )