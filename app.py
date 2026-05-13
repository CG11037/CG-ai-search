import os
import json
from dotenv import load_dotenv
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# 官方 Tavily 客户端
from tavily import TavilyClient

# LangChain 用于 DeepSeek 模型调用
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

# 加载 .env 文件中的环境变量
load_dotenv()

app = FastAPI(title="CG AI Search API")

# 跨域设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- 配置 ----------
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
MODEL_NAME = os.getenv("MODEL_NAME", "deepseek-v4-flash")

if not TAVILY_API_KEY or not DEEPSEEK_API_KEY:
    raise RuntimeError("请在 .env 文件中设置 TAVILY_API_KEY 和 DEEPSEEK_API_KEY")

# 初始化客户端
tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
llm = ChatOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
    model=MODEL_NAME,
    temperature=0.3,
    streaming=True,
)


class SearchRequest(BaseModel):
    query: str


async def generate_ai_answer(query: str, search_results: list):
    """将搜索结果作为上下文，流式生成回答"""
    # 构建引用文本
    sources_text = ""
    for i, res in enumerate(search_results, start=1):
        title = res.get("title", "无标题")
        snippet = res.get("snippet") or res.get("content", "")
        url = res.get("url", "")
        sources_text += f"[{i}] {title}\n{snippet}\n来源: {url}\n\n"

    system_prompt = (
        "你是一个智能搜索引擎助手。请根据以下搜索结果，综合回答用户的问题。\n"
        "要求：\n"
        "1. 回答需要引用具体来源，在正文中用 [编号] 标注（如 [1]）。\n"
        "2. 如果搜索结果不足以回答问题，请说明情况。\n"
        "3. 回答必须严格参考搜索结果\n"
        "4. 使用 Markdown 格式排版。\n"
        "5. 回答要简洁、客观、信息量大。"
    )

    user_prompt = f"搜索结果：\n{sources_text}\n\n用户问题：{query}\n请综合以上信息给出回答："

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    full_response = ""
    async for chunk in llm.astream(messages):
        if chunk.content:
            full_response += chunk.content
            yield {"type": "token", "token": chunk.content}

    # 回答完成后，生成相关问题
    related_questions = await generate_related_questions(query, full_response)
    yield {"type": "related", "questions": related_questions}

    # 最后传递完整的搜索结果
    yield {"type": "done", "all_results": search_results}


async def generate_related_questions(original_query: str, answer: str) -> list:
    """用模型生成 3~5 个相关问题"""
    prompt = f"""根据用户问题"{original_query}"和AI回答，生成3-5个用户可以继续探索的相关问题。
请直接返回问题列表，每行一个，不要编号，不要其他文字。"""
    messages = [HumanMessage(content=prompt)]
    response = await llm.ainvoke(messages)
    questions = [q.strip() for q in response.content.strip().split("\n") if q.strip()]
    return questions[:5]


@app.post("/api/search")
async def search_endpoint(request: SearchRequest):
    query = request.query

    # 1. 调用 Tavily 搜索
    try:
        # 注意：新版本 tavily-python 的 search 方法直接返回结果
        # 返回值可能是 dict 或 list，这里做兼容处理
        raw_response = tavily_client.search(query, max_results=5, search_depth="basic")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")

    # 解析搜索结果
    if isinstance(raw_response, dict):
        raw_results = raw_response.get("results", [])
    elif isinstance(raw_response, list):
        raw_results = raw_response
    else:
        raw_results = []

    # 统一结构
    all_results = []
    for idx, r in enumerate(raw_results):
        all_results.append({
            "index": idx + 1,
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("snippet") or r.get("content", ""),
            "content": r.get("content", ""),
            "favicon": "",
        })

    # 2. SSE 流式响应
    async def event_stream():
        # 先发送来源信息
        yield {"type": "sources", "sources": all_results}
        # 再发送 AI 生成内容
        async for event in generate_ai_answer(query, all_results):
            yield event

    async def sse_wrapper():
        async for event in event_stream():
            yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_wrapper(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# 托管前端页面
import os as _os
static_dir = _os.path.join(_os.path.dirname(__file__), "static")
if _os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    @app.get("/")
    async def root():
        return {"message": "请将前端 index.html 放入 static 文件夹"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)