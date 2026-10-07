import streamlit as st
import google.generativeai as genai
from pypdf import PdfReader
import json
import pandas as pd

# 初始化 Session State (用來記住使用者的進度與錯題)
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
    uploaded_file = st.file_uploader("上傳 PDF 考古題", type="pdf")
    
    if st.button("清空錯題本"):
        st.session_state.wrong_bank = []
        st.success("錯題本已清空！")

# 處理上傳的 PDF 並交給 AI 解析
if uploaded_file and api_key:
    if st.button("🚀 開始自動解析 PDF 題目"):
        with st.spinner("AI 正在讀取並整理題目中，請稍候... (如果題目較多，可能需要 1~3 分鐘)") :
            try:
                # 1. 讀取 PDF 文字
                reader = PdfReader(uploaded_file)
                pdf_text = "".join([page.extract_text() for page in reader.pages])
                
                # 2. 設定 Gemini 模型 (已更新為系統指定的 gemini-3.8-flash)
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(
                    model_name="gemini-3.8-flash",
                    generation_config={"response_mime_type": "application/json"}
                )
                
                # 3. 提示詞：要求 AI 整理成 JSON 格式，並提供逐項解析
                prompt = f"""
                你是一個專業的考試導師。請將以下考古題文字，轉換為選擇題陣列。
                每個題目必須包含以下 JSON 結構：
                [
                  {{
                    "question": "題目內容",
                    "options": ["A. 選項一", "B. 選項二", "C. 選項三", "D. 選項四"],
                    "answer": "正確答案的完整文字 (必須完全等於 options 裡的其中一項)",
                    "explanation": "逐項詳細解析，說明正確選項為何正確，以及其他三個選項為何錯誤。"
                  }}
                ]
                以下是題目文字：
                {pdf_text[:30000]} 
                """
                
                response = model.generate_content(prompt)
                
                # 4. 儲存到系統狀態中
                st.session_state.questions = json.loads(response.text)
                st.session_state.current_index = 0
                st.session_state.show_explanation = False
                st.success(f"解析完成！共找到 {len(st.session_state.questions)} 題。")
                
            except Exception as e:
                st.error(f"解析失敗，請確認 API Key 是否正確，或 PDF 文字是否可讀取。錯誤訊息: {e}")

# 主要刷題介面
if st.session_state.questions:
    current_q = st.session_state.questions[st.session_state.current_index]
    
    st.subheader(f"第 {st.session_state.current_index + 1} 題 / 共 {len(st.session_state.questions)} 題")
    st.markdown(f"**{current_q['question']}**")
    
    # 選項按鈕
    user_choice = st.radio("請選擇答案：", current_q['options'], index=None)
    
    if st.button("送出答案"):
        if user_choice:
            st.session_state.show_explanation = True
            if user_choice == current_q['answer']:
                st.success("🎉 答對了！")
            else:
                st.error("❌ 答錯了！已自動加入錯題本。")
                # 避免重複加入錯題本
                if current_q not in st.session_state.wrong_bank:
                    st.session_state.wrong_bank.append(current_q)
        else:
            st.warning("請先選擇一個答案喔！")
            
    # 顯示解析與下一題按鈕
    if st.session_state.show_explanation:
        st.info(f"**正確答案：** {current_q['answer']}\n\n**🔍 逐項解析：**\n{current_q['explanation']}")
        
        if st.session_state.current_index < len(st.session_state.questions) - 1:
            if st.button("下一題 ➡️"):
                st.session_state.current_index += 1
                st.session_state.show_explanation = False
                st.rerun()
        else:
            st.balloons()
            st.success("您已完成所有題目！")

# 錯題本區域
if st.session_state.wrong_bank:
    st.divider()
    st.subheader("📚 我的錯題收藏區")
    
    # 轉換成表格方便查看與下載
    df_wrong = pd.DataFrame(st.session_state.wrong_bank)
    st.dataframe(df_wrong[['question', 'answer', 'explanation']], hide_index=True)
    
    # 支援下載錯題本
    csv = df_wrong.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 下載錯題本 (CSV格式)",
        data=csv,
        file_name='my_wrong_questions.csv',
        mime='text/csv',
    )
elif not st.session_state.questions:
    st.info("請從左側欄位輸入 API Key 並上傳 PDF 開始刷題！")