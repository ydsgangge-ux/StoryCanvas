"""StoryCanvas - 自由画布叙事创作系统"""
import sys
import os
import asyncio
from contextlib import asynccontextmanager

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Dict
from backend.core.database import init_db, get_connection
from backend.core.config import settings
from backend.core.snapshot import auto_snapshot_loop
from backend.api import projects, blocks, connections, canvas, generate, export_import, snapshots_api
from backend.story_cards import cards
from backend.llm.ollama import OllamaProvider


class LLMSettingsUpdate(BaseModel):
    provider: str
    configs: Dict[str, dict]
    image_provider: Optional[str] = None
    image_configs: Optional[Dict[str, dict]] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    # 启动所有项目的自动快照任务
    try:
        conn = get_connection()
        project_ids = conn.execute("SELECT id FROM projects").fetchall()
        conn.close()
        if not hasattr(app, "_snapshot_tasks"):
            app._snapshot_tasks = []
        for proj in project_ids:
            task = asyncio.create_task(auto_snapshot_loop(proj["id"]))
            app._snapshot_tasks.append(task)
        print(f"  [OK] 自动快照任务已启动 ({len(project_ids)} 个项目)")
    except Exception as e:
        print(f"  [SKIP] 自动快照启动跳过: {e}")
    print(f"  [OK] 数据库初始化完成")
    print(f"  [OK] LLM后端: {settings.llm_provider}")
    print(f"  [OK] 服务端口: {settings.port}")
    yield
    # Shutdown
    print("服务已停止")


app = FastAPI(
    title="StoryCanvas",
    description="自由画布叙事创作系统 API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件 - 图片生成结果
IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "images")
os.makedirs(IMAGE_DIR, exist_ok=True)
app.mount("/images", StaticFiles(directory=IMAGE_DIR), name="images")

# Register routers
app.include_router(projects.router)
app.include_router(blocks.router)
app.include_router(connections.router)
app.include_router(canvas.router)
app.include_router(generate.router)
app.include_router(export_import.router)
app.include_router(snapshots_api.router)


@app.get("/api/story-cards")
def list_story_cards():
    """获取所有故事卡"""
    return cards.list_cards()


@app.get("/api/story-cards/{card_id}")
def get_story_card(card_id: str):
    """获取单张故事卡详情"""
    card = cards.get_card(card_id)
    if not card:
        from fastapi import HTTPException
        raise HTTPException(404, f"故事卡 {card_id} 不存在")
    return card


@app.get("/api/health")
def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/api/projects/{project_id}/foreshadows")
def get_foreshadows(project_id: str):
    """获取所有铺垫/悬念状态"""
    from backend.core.database import get_connection
    import json
    conn = get_connection()
    hooks = conn.execute(
        "SELECT id, content, type FROM blocks WHERE project_id = ? AND type IN ('HOOK', 'FORESHADOW')",
        (project_id,)
    ).fetchall()
    conn.close()
    result = []
    for h in hooks:
        hc = json.loads(h["content"] or "{}")
        result.append({
            "id": h["id"],
            "type": h["type"],
            "title": hc.get("title", ""),
            "status": hc.get("status", "open"),
            "urgency": hc.get("urgency", ""),
            "plant_chapter": hc.get("plant_chapter", ""),
            "payoff_chapter": hc.get("payoff_chapter", ""),
            "description": hc.get("description", hc.get("hint_content", "")),
        })
    return result


@app.get("/api/projects/{project_id}/character-arcs")
def get_character_arcs(project_id: str):
    """获取所有角色情感弧线数据"""
    from backend.core.database import get_connection
    import json
    conn = get_connection()
    chars = conn.execute("SELECT id, content FROM blocks WHERE project_id = ? AND type = 'CHARACTER'", (project_id,)).fetchall()
    growths = conn.execute("SELECT id, content FROM blocks WHERE project_id = ? AND type = 'GROWTH'", (project_id,)).fetchall()
    conn.close()
    char_map = {}
    for c in chars:
        cc = json.loads(c["content"] or "{}")
        char_map[c["id"]] = {"id": c["id"], "name": cc.get("name", ""), "arc_type": "", "start_state": "", "end_state": "", "keystone_moments": ""}
    for g in growths:
        gc = json.loads(g["content"] or "{}")
        owner_id = gc.get("character_id", "")
        if owner_id in char_map:
            char_map[owner_id]["arc_type"] = gc.get("arc_type", "")
            char_map[owner_id]["start_state"] = gc.get("start_state", "")
            char_map[owner_id]["end_state"] = gc.get("end_state", "")
            char_map[owner_id]["keystone_moments"] = gc.get("keystone_moments", "")
    return list(char_map.values())


@app.get("/api/projects/{project_id}/relationship-map")
def get_relationship_map(project_id: str):
    """获取关系网络图数据"""
    from backend.core.database import get_connection
    import json
    conn = get_connection()
    rels = conn.execute("SELECT id, content FROM blocks WHERE project_id = ? AND type = 'RELATIONSHIP'", (project_id,)).fetchall()
    chars = conn.execute("SELECT id, content FROM blocks WHERE project_id = ? AND type = 'CHARACTER'", (project_id,)).fetchall()
    conn.close()
    char_names = {}
    for c in chars:
        cc = json.loads(c["content"] or "{}")
        char_names[c["id"]] = cc.get("name", c["id"])
    result = []
    for r in rels:
        c = json.loads(r["content"] or "{}")
        a_id = c.get("party_a_id", "")
        b_id = c.get("party_b_id", "")
        result.append({
            "id": r["id"],
            "party_a_id": a_id,
            "party_b_id": b_id,
            "party_a": char_names.get(a_id, a_id),
            "party_b": char_names.get(b_id, b_id),
            "type": c.get("relationship_type", ""),
            "intensity": c.get("intensity", 0),
            "dynamic": c.get("dynamic", ""),
            "evolution": c.get("evolution", ""),
        })
    return result


@app.get("/api/projects/{project_id}/timeline-view")
def get_timeline_view(project_id: str):
    """获取多线叙事时间线视图数据"""
    from backend.core.database import get_connection
    import json
    conn = get_connection()
    timelines = conn.execute("SELECT id, content FROM blocks WHERE project_id = ? AND type = 'TIMELINE'", (project_id,)).fetchall()
    scenes = conn.execute("SELECT id, content, chapter_pos, timeline_id FROM blocks WHERE project_id = ? AND type = 'SCENE'", (project_id,)).fetchall()
    conn.close()
    result = []
    for t in timelines:
        tc = json.loads(t["content"] or "{}")
        related_scenes = [{"id": s["id"], "title": (json.loads(s["content"] or "{}")).get("title", ""), "chapter_pos": s["chapter_pos"]} for s in scenes if s["timeline_id"] == t["id"]]
        result.append({"id": t["id"], "name": tc.get("timeline_name", ""), "type": tc.get("timeline_type", "main"), "scenes": related_scenes})
    return result


@app.get("/api/projects/{project_id}/information-check")
def get_information_check(project_id: str):
    """信息边界违规检测"""
    from backend.core.database import get_connection
    from backend.narrative.validator import InformationValidator
    import json
    conn = get_connection()
    chapters = conn.execute("SELECT chapter_num, content FROM chapters WHERE project_id = ? AND content IS NOT NULL", (project_id,)).fetchall()
    boundaries = conn.execute("SELECT id, content FROM blocks WHERE project_id = ? AND type = 'INFORMATION_BOUNDARY'", (project_id,)).fetchall()
    chars = conn.execute("SELECT id, content FROM blocks WHERE project_id = ? AND type = 'CHARACTER'", (project_id,)).fetchall()
    conn.close()
    char_names = {}
    for c in chars:
        cc = json.loads(c["content"] or "{}")
        char_names[c["id"]] = cc.get("name", c["id"])
    char_boundaries = {}
    for b in boundaries:
        bc = json.loads(b["content"] or "{}")
        owner_id = bc.get("character_id", b["id"])
        doesnt_know = []
        for item in bc.get("wrongly_believes", []):
            if isinstance(item, dict):
                doesnt_know.append(item.get("belief", item.get("info", "")))
            elif isinstance(item, str) and item:
                doesnt_know.append(item)
        for item in bc.get("confirmed_knowledge", []):
            if isinstance(item, dict):
                info_text = item.get("info", "")
                if info_text and item.get("source") == "meta":
                    doesnt_know.append(info_text)
        if doesnt_know:
            char_boundaries[owner_id] = {"doesnt_know": [x for x in doesnt_know if x], "name": char_names.get(owner_id, owner_id)}
    validator = InformationValidator()
    all_violations = []
    for ch in chapters:
        violations = validator.validate(ch["content"] or "", char_boundaries)
        for v in violations:
            v["chapter_num"] = ch["chapter_num"]
            v["character_name"] = char_names.get(v.get("character", ""), v.get("character", ""))
            all_violations.append(v)
    return {"violations": all_violations, "total": len(all_violations)}


@app.get("/api/projects/{project_id}/narrative-tracking")
def get_narrative_tracking(project_id: str):
    """获取叙事追踪数据"""
    from backend.core.database import get_connection
    import json
    conn = get_connection()

    # 伏笔状态
    hooks = conn.execute(
        "SELECT id, type, content FROM blocks WHERE project_id = ? AND type IN ('HOOK', 'FORESHADOW')",
        (project_id,)
    ).fetchall()

    foreshadows = []
    for h in hooks:
        hc = json.loads(h["content"] or "{}")
        foreshadows.append({
            "id": h["id"],
            "type": h["type"],
            "title": hc.get("title", "未命名"),
            "status": hc.get("status", "open"),
        })

    # 角色弧线
    chars = conn.execute(
        "SELECT id, content FROM blocks WHERE project_id = ? AND type = 'CHARACTER'",
        (project_id,)
    ).fetchall()
    character_arcs = []
    for c in chars:
        cc = json.loads(c["content"] or "{}")
        character_arcs.append({
            "id": c["id"],
            "name": cc.get("name", "未命名"),
            "arc_type": cc.get("arc_type", "未设定"),
        })

    conn.close()
    return {"foreshadows": foreshadows, "character_arcs": character_arcs}


@app.get("/api/projects/{project_id}/export")
def export_project(project_id: str):
    """导出全书为Markdown"""
    from backend.core.database import get_connection
    conn = get_connection()
    project = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    chapters = conn.execute(
        "SELECT * FROM chapters WHERE project_id = ? AND status != 'planned' ORDER BY chapter_num ASC",
        (project_id,)
    ).fetchall()
    conn.close()

    if not project:
        raise HTTPException(404, "项目不存在")

    lines = [f"# {project['title']}\n"]
    for ch in chapters:
        lines.append(f"\n## 第{ch['chapter_num']}章 {ch.get('title', '') or ''}\n")
        if ch["content"]:
            lines.append(ch["content"] + "\n")

    return {"title": project["title"], "content": "\n".join(lines)}


@app.get("/api/settings")
def get_settings():
    """获取系统设置（含LLM配置，隐藏API Key）"""
    full = settings.get_settings_dict()
    # Mask API keys for security
    masked = {"provider": full.get("provider", "deepseek")}
    masked_configs = {}
    for provider_name, cfg in full.get("configs", {}).items():
        masked_cfg = dict(cfg)
        for key in list(masked_cfg.keys()):
            if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower():
                if masked_cfg[key]:
                    masked_cfg[key] = masked_cfg[key][:8] + "..." + masked_cfg[key][-4:] if len(masked_cfg[key]) > 16 else "****"
        masked_configs[provider_name] = masked_cfg
    masked["configs"] = masked_configs
    # 图片生成配置
    masked["image_provider"] = full.get("image_provider", "zhipu_image")
    masked_image_configs = {}
    for provider_name, cfg in full.get("image_configs", {}).items():
        masked_cfg = dict(cfg)
        for key in list(masked_cfg.keys()):
            if "key" in key.lower() or "token" in key.lower() or "secret" in key.lower():
                if masked_cfg[key]:
                    masked_cfg[key] = masked_cfg[key][:8] + "..." + masked_cfg[key][-4:] if len(masked_cfg[key]) > 16 else "****"
        masked_image_configs[provider_name] = masked_cfg
    masked["image_configs"] = masked_image_configs
    # Add default models list for each provider
    masked["available_models"] = {
        "deepseek": ["deepseek-chat", "deepseek-reasoner"],
        "openai": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo", "o1", "o1-mini", "o3-mini"],
        "claude": ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307",
                   "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
        "gemini": ["gemini-1.5-pro", "gemini-1.5-flash", "gemini-2.0-flash", "gemini-2.0-pro"],
        "ollama": ["llama3.1", "llama3.2", "qwen2.5", "mistral", "mixtral", "gemma2", "deepseek-r1"],
    }
    return masked


@app.put("/api/settings")
def update_settings(req: LLMSettingsUpdate):
    """更新系统设置"""
    update_data = {"provider": req.provider, "configs": req.configs}
    if req.image_provider is not None:
        update_data["image_provider"] = req.image_provider
    if req.image_configs is not None:
        update_data["image_configs"] = req.image_configs
    settings.update_settings(update_data)
    return {"message": "设置已保存", "provider": req.provider}


@app.get("/api/settings/ollama-models")
async def list_ollama_models():
    """获取Ollama本地已安装的模型列表"""
    provider = OllamaProvider(
        base_url=settings.ollama_base_url,
        model=settings.ollama_model
    )
    models = await provider.list_models()
    return {"models": models}


@app.post("/api/settings/test-connection")
async def test_llm_connection(req: LLMSettingsUpdate):
    """测试LLM连接是否正常"""
    from backend.llm.base import create_llm
    # Temporarily override settings
    old_provider = settings._llm_settings.get("provider")
    old_configs = settings._llm_settings.get("configs", {})
    try:
        settings._llm_settings["provider"] = req.provider
        settings._llm_settings["configs"] = req.configs
        llm = create_llm()
        result = await llm.chat(
            "你是一个测试助手。",
            "请回复'连接成功'四个字。",
            temperature=0.1
        )
        return {"success": True, "response": result[:100]}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        settings._llm_settings["provider"] = old_provider
        settings._llm_settings["configs"] = old_configs


if __name__ == "__main__":
    import uvicorn
    print("""
    ╔══════════════════════════════════════════╗
    ║        StoryCanvas - 叙事创作系统         ║
    ║    自由画布 · AI辅助 · 多线叙事           ║
    ╚══════════════════════════════════════════╝
    """)
    uvicorn.run("backend.main:app", host="0.0.0.0", port=settings.port, reload=True)
