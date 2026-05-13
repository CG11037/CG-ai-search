# CG AI Search - 智能联网搜索引擎

AI 驱动的搜索引擎，用户用自然语言提问，系统自动联网获取最新信息，由大模型生成带引用来源的综合回答。

## 功能

- AI 综合回答：基于实时搜索结果生成智能总结，支持 Markdown 排版与代码高亮
- 来源引用：回答中自动标注编号，底部列出所有引用来源，可点击跳转原文
- 完整搜索结果列表：同时展示所有搜索结果，包括 AI 未引用的结果
- 流式打字效果：回答逐字实时显示，体验流畅
- 本地搜索历史：自动保存历史记录，一键复用
- 相关问题推荐：回答完成后生成3-5个延伸问题
- 浅色/深色主题：黑白极简设计，所有边框均为直角

## 技术栈

| 层面 | 技术 |
|------|------|
| 前端 | Vue 3 (CDN)、marked.js、highlight.js |
| 后端 | Python 3.10+、FastAPI、Uvicorn |
| AI 编排 | LangChain、langchain-openai |
| 模型 | DeepSeek V4 (兼容 OpenAI SDK) |
| 搜索 | Tavily Search API (实时网页搜索) |
| 部署 | Render (Python Web Service) |

## 本地运行
```bash
# 1. 克隆仓库
git clone https://github.com/CG11037/CG-ai-search.git
cd cg-ai-search

# 2. 创建虚拟环境并激活
python3 -m venv ai-search-venv
source ai-search-venv/bin/activate   # Windows: venv\Scripts\activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置环境变量（创建 .env 文件）
export TAVILY_API_KEY="你的Tavily密钥"
export DEEPSEEK_API_KEY="你的DeepSeek密钥"

# 5. 启动服务
python app.py

# 6. 浏览器打开 http://localhost:8000