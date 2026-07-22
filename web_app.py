# -*- coding: utf-8 -*-
"""
网页版：大学生职业生涯 AI 规划师 (最终纯净版)
"""
import streamlit as st
import os
import re
import json
import time
from datetime import datetime
from openai import OpenAI

# ====== 配置区 ======
API_KEY = st.secrets.get("BAILIAN_API_KEY", "")
if not API_KEY:
    st.error("⚠️ 请在 Streamlit Cloud 的【设置】->【密钥】中配置 BAILIAN_API_KEY")
    st.stop()

BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL = "qwen-plus"

client = OpenAI(api_key=API_KEY, base_url=BASE_URL)

# ============================================================
# 🛠️ 核心函数
# ============================================================
def call_ai(user_prompt: str, system_prompt: str = None) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    try:
        response = client.chat.completions.create(model=MODEL, messages=messages, temperature=0.7)
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ API 调用出错：{e}"

def extract_json(text: str):
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if m:
        try:
            return json.loads(m.group(1))
        except:
            pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except:
            pass
    return {}

# ====== 侧边栏：自由提问 ======
with st.sidebar:
    st.header("💬 自由咨询")
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    user_question = st.chat_input("输入你想了解的AI职业问题...")
    if user_question:
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        with st.chat_message("user"):
            st.write(user_question)
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                response = call_ai(user_question, "你是一个专业的职业规划导师，请用简短易懂的语言回答高中或大学生关于专业、职业的问题。")
                st.write(response)
                st.session_state.chat_history.append({"role": "assistant", "content": response})

# ====== 主页面 ======
st.set_page_config(page_title="AI职业规划师", layout="wide")
st.title("🎓 AI 职业规划与模拟面试系统")

# 状态管理
if 'step' not in st.session_state: st.session_state.step = 'input'
if 'match_data' not in st.session_state: st.session_state.match_data = {}
if 'questions' not in st.session_state: st.session_state.questions = []
if 'question_idx' not in st.session_state: st.session_state.question_idx = 0
if 'answers' not in st.session_state: st.session_state.answers = []
if 'evaluations' not in st.session_state: st.session_state.evaluations = []
if 'extra_advice' not in st.session_state: st.session_state.extra_advice = ""
if 'report_html' not in st.session_state: st.session_state.report_html = ""

# ---------- 1. 输入信息 ----------
if st.session_state.step == 'input':
    st.markdown("### 🎯 第一步：填写你的背景与意向岗位")
    with st.form("input_form"):
        col1, col2 = st.columns(2)
        target = col1.text_input("🎯 意向岗位")
        major = col2.text_input("📚 你的专业")
        skills = st.text_input("🛠️ 掌握的技能")
        submitted = st.form_submit_button("📝 提交并生成面试题")
        
        if submitted:
            if not target or not major or not skills:
                st.error("⚠️ 所有输入都不能为空！")
            else:
                with st.spinner("🤖 正在进行人岗匹配，并为你生成模拟面试题..."):
                    sys_p = "你是一位资深HRD，严格以JSON格式输出，不要多余的文字。"
                    usr_p = f"""请对以下候选人进行人岗匹配分析：【意向岗位】{target}【所学专业】{major}【掌握技能】{skills}请严格按以下JSON格式输出：{{"target_position":"{target}","major":"{major}","skills":"{skills}","overall_score":<0-100>,"core_strengths":["优势1","优势2","优势3"],"fatal_weaknesses":["短板1","短板2","短板3"],"dimension_scores":{{"专业度":0-100,"沟通表达":0-100,"逻辑思维":0-100,"行业认知":0-100,"实操落地":0-100}},"hrd_comment":"<80字点评>"}}"""
                    raw = call_ai(usr_p, sys_p)
                    data = extract_json(raw)
                    data.setdefault("target_position", target)
                    data.setdefault("major", major)
                    data.setdefault("skills", skills)
                    data.setdefault("overall_score", 60)
                    data.setdefault("core_strengths", ["学习能力强", "专业匹配", "基础扎实"])
                    data.setdefault("fatal_weaknesses", ["经验不足", "行业认知浅", "缺少项目"])
                    data.setdefault("hrd_comment", "基础不错，但需加强实践和行业了解。")
                    default_dims = {k: data["overall_score"] for k in ["专业度", "沟通表达", "逻辑思维", "行业认知", "实操落地"]}
                    for k in default_dims:
                        if k not in data.get("dimension_scores", {}):
                            data["dimension_scores"][k] = default_dims[k]
                    st.session_state.match_data = data

                    q_sys = "你是一位严格的大厂面试官。请只输出 JSON 数组，包含 5 道面试题。"
                    q_usr = f"""目标岗位：{target}，候选人背景：{major}专业，掌握 {skills}。请生成 5 道结构化面试题（难度递进），涵盖：自我认知类、专业能力类、情景行为类。JSON格式：[{{"type":"类型","question":"题目"}}]"""
                    q_raw = call_ai(q_usr, q_sys)
                    questions = []
                    m = re.search(r"\[.*\]", q_raw, re.DOTALL)
                    if m:
                        try: questions = json.loads(m.group(0))
                        except: pass
                    if not questions:
                        questions = [{"type": "综合", "question": f"你为什么想做 {target} 这个岗位？"}, {"type": "专业", "question": "你最擅长的技能是什么？"}, {"type": "专业", "question": "请描述一次你独立解决问题的经历。"}, {"type": "实操", "question": "遇到完全不会的问题你会怎么处理？"}, {"type": "情景", "question": "如果你与同事意见不合，你会怎么办？"}]
                    st.session_state.questions = questions
                    st.session_state.question_idx = 0
                    st.session_state.answers = []
                    st.session_state.evaluations = []
                    st.session_state.step = 'interview'
                    st.rerun()

# ---------- 2. 多轮面试问答 ----------
if st.session_state.step == 'interview':
    idx = st.session_state.question_idx
    total = len(st.session_state.questions)
    q_data = st.session_state.questions[idx]
    st.markdown(f"### 🎤 模拟面试：第 {idx+1} / {total} 题")
    st.info(f"**{q_data.get('type', '综合')}类问题：** {q_data['question']}")
    with st.form(f"answer_question_{idx}"):
        ans = st.text_area("✍️ 输入你的回答：", height=150)
        submit_ans = st.form_submit_button("✅ 提交回答")
        if submit_ans:
            if not ans.strip():
                st.warning("回答不能为空，请写点什么！")
            else:
                st.session_state.answers.append(ans)
                with st.spinner("🤖 面试官正在对你的回答进行点评..."):
                    eval_sys = "你是大厂面试官。针对回答给出简短评价（60字内），指出亮点不足，给0-100分。JSON格式：{\"score\":<分数>,\"comment\":\"<评价>\"}"
                    eval_raw = call_ai(f"题目：{q_data['question']}\n回答：{ans}", eval_sys)
                    eval_data = extract_json(eval_raw)
                    score = eval_data.get("score", 70)
                    comment = eval_data.get("comment", "回答基本完整，深度还可加强。")
                    st.session_state.evaluations.append({"score": score, "comment": comment})
                if st.session_state.question_idx + 1 < total:
                    st.session_state.question_idx += 1
                    st.rerun()
                else:
                    st.session_state.step = 'analysis'
                    st.rerun()

# ---------- 3. 生成报告与分析 ----------
if st.session_state.step == 'analysis':
    st.markdown("### 📊 正在生成专属职业规划与面试复盘报告...")
    data = st.session_state.match_data
    with st.spinner("🎨 正在生成深度的职业建议和可视化雷达图..."):
        sys_advice = "你是一位资深的职业规划导师。根据候选人回答的面试情况，给出3条具体的学习建议，弥补短板。"
        qa_summary = "\n".join([f"Q{i+1}: {q['question']}\nA: {st.session_state.answers[i]}" for i, q in enumerate(st.session_state.questions)])
        usr_advice = f"目标岗位 {data['target_position']}。面试回顾：{qa_summary}"
        extra_advice_text = call_ai(usr_advice, sys_advice)
        st.session_state.extra_advice = extra_advice_text

        dims = data["dimension_scores"]
        radar_vals = [int(dims.get(d, data["overall_score"])) for d in ["专业度", "沟通表达", "逻辑思维", "行业认知", "实操落地"]]
        strengths_html = "".join([f"<li>{s}</li>" for s in data["core_strengths"]])
        weaknesses_html = "".join([f"<li>{w}</li>" for w in data["fatal_weaknesses"]])
        details_html = "".join([f"<div class='qa-item'><b>Q{i+1}:</b> {q['question']}<br><b>A:</b> {st.session_state.answers[i]}<br><b>评价：</b> {st.session_state.evaluations[i]['comment']}</div>" for i, q in enumerate(st.session_state.questions)])
        advice_html = extra_advice_text.replace("\n", "<br>")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        html_content = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<style>body{{font-family:sans-serif;background:#667eea;padding:30px;}}.card{{background:white;border-radius:12px;padding:30px;margin:20px auto;max-width:900px;box-shadow:0 10px 30px rgba(0,0,0,0.15);}}h1{{text-align:center;color:#2a5298;}}.score-circle{{width:160px;height:160px;border-radius:50%;background:conic-gradient(#667eea 0% {data['overall_score']}%, #e0e0e0 {data['overall_score']}% 100%);margin:20px auto;display:flex;justify-content:center;align-items:center;position:relative;}}.score-circle::before{{content:'';position:absolute;width:130px;height:130px;border-radius:50%;background:white;}}.score-text{{position:relative;z-index:1;font-size:2.8em;font-weight:bold;color:#2a5298;}}#radar-chart{{width:100%;height:400px;}}.qa-item{{border-left:4px solid #667eea;padding:10px 20px;margin:15px 0;background:#f8f9fa;border-radius:6px;}}</style></head>
<body><div class="card"><h1>🎓 职业生涯 AI 规划报告</h1>
<p><strong>意向岗位：</strong>{data['target_position']} | <strong>专业：</strong>{data['major']}</p>
<div class="score-circle"><div class="score-text">{data['overall_score']}</div></div>
<h3>💪 优势</h3><ul>{strengths_html}</ul>
<h3>⚠️ 短板</h3><ul>{weaknesses_html}</ul>
<h3>💬 HRD 点评</h3><p>{data['hrd_comment']}</p>
<h3>📝 模拟面试记录与复盘</h3>
{details_html}
<h3>🚀 职业进阶建议</h3>
<div>{advice_html}</div>
<h2>🎯 能力画像</h2><div id="radar-chart"></div>
</div>
<script>var chart=echarts.init(document.getElementById('radar-chart'));chart.setOption({{radar:{{indicator:[{{name:'专业度',max:100}},{{name:'沟通表达',max:100}},{{name:'逻辑思维',max:100}},{{name:'行业认知',max:100}},{{name:'实操落地',max:100}}],center:['50%','55%'],radius:'70%'}},series:[{{type:'radar',data:[{{value:{json.dumps(radar_vals)},name:'评估'}}]}}]}});window.addEventListener('resize',function(){{chart.resize();}});</script></body></html>"""
        st.session_state.report_html = html_content
        st.session_state.step = 'done'
        st.rerun()

# ---------- 4. 展示最终结果 ----------
if st.session_state.step == 'done':
    st.success("🎉 全部完成！你的专属规划报告已生成。")
    st.markdown("### 📄 模拟面试复盘与职业规划建议")
    st.write(st.session_state.extra_advice)
    st.divider()
    st.download_button(
        label="📥 下载完整的 HTML 报告 (双击查看雷达图)",
        data=st.session_state.report_html,
        file_name=f"career_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html",
        mime="text/html"
    )
    st.caption("💡 提示：下载后双击用浏览器打开，按键盘 `Ctrl+P` 即可直接导出为 PDF。")
    st.divider()
    if st.button("🔄 重新测试其他职业"):
        for key in ['step', 'match_data', 'questions', 'question_idx', 'answers', 'evaluations', 'extra_advice', 'report_html']:
            if key in st.session_state: del st.session_state[key]
        st.rerun()
