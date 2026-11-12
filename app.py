import asyncio
import os
import time
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

API_URL = "https://backboard.railway.com/graphql/v2"
TOKEN = os.getenv("RAILWAY_TOKEN", "")
WORKSPACE_ID = os.getenv("RAILWAY_WORKSPACE_ID", "d72e603c-7a51-417e-984a-35edeb307cbf")
CACHE_SECONDS = int(os.getenv("CACHE_SECONDS", "60"))

app = FastAPI(title="MAKUMAKUBOT Status")
_cache = {"at": 0.0, "data": None}
_lock = asyncio.Lock()

PAGE = r"""<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#10141d"><title>MAKUMAKUBOT Status</title>
<style>
:root{color-scheme:dark;--bg:#0d1119;--panel:#151c28;--line:#283244;--muted:#91a0b5;--text:#edf2fa;--green:#39c98a;--red:#ff6b75;--yellow:#f2bd58;--blue:#78aaff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at top,#172235 0,#0d1119 48%);color:var(--text);font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1000px;margin:0 auto;padding:44px 22px 72px}.top{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}
.brand{font-size:13px;letter-spacing:.15em;color:var(--blue);font-weight:700}.updated{color:var(--muted);font-size:13px}
h1{font-size:clamp(30px,5vw,46px);letter-spacing:-.04em;margin:12px 0 8px}.sub{color:var(--muted);margin:0 0 28px}
.overview{border:1px solid var(--line);background:linear-gradient(135deg,#1b2939,#151c28);border-radius:18px;padding:22px;display:flex;align-items:center;gap:18px;margin-bottom:20px}
.pulse{width:13px;height:13px;border-radius:50%;background:var(--green);box-shadow:0 0 0 6px #39c98a22;flex:none}.overview.bad .pulse{background:var(--red);box-shadow:0 0 0 6px #ff6b7522}.overview.warn .pulse{background:var(--yellow);box-shadow:0 0 0 6px #f2bd5822}
.overview strong{font-size:20px;display:block}.overview small{color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:18px 0 32px}.stat,.project{border:1px solid var(--line);background:#151c28dd;border-radius:14px}.stat{padding:16px}.stat span{display:block;color:var(--muted);font-size:12px}.stat b{font-size:27px}
h2{font-size:18px;margin:30px 0 12px}.project{padding:18px;margin:12px 0}.project-head{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:12px}.project h3{margin:0;font-size:16px}.count{font-size:12px;color:var(--muted)}
.service{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:12px 2px;border-top:1px solid #283244aa}.service-name{font-weight:550;overflow-wrap:anywhere}.pill{white-space:nowrap;font-size:12px;padding:4px 9px;border-radius:999px;background:#283244;color:var(--muted)}
.pill.online{background:#123c30;color:#73e2b2}.pill.error{background:#49252d;color:#ff9aa1}.pill.deploying{background:#49391e;color:#f4ce82}.pill.sleeping{background:#203653;color:#a9cbff}
.empty,.notice{color:var(--muted);font-size:13px}.notice{border:1px solid var(--line);border-radius:12px;padding:14px;margin-top:18px}
footer{border-top:1px solid var(--line);margin-top:34px;padding-top:18px;color:var(--muted);font-size:12px}
@media(max-width:620px){main{padding:28px 15px 50px}.stats{grid-template-columns:repeat(2,1fr)}.overview{padding:17px}.project{padding:15px}}
</style></head><body><main>
<div class="top"><div class="brand">MAKUMAKUBOT / SYSTEM STATUS</div><div class="updated" id="updated">状態を取得しています…</div></div>
<h1>サービス稼働状況</h1><p class="sub">Railway上のサービス状態を表示します。</p>
<div class="overview" id="overall"><i class="pulse"></i><div><strong id="headline">状態を確認中</strong><small id="summary">最新の情報を取得しています。</small></div></div>
<div class="stats">
<div class="stat"><span>総サービス数</span><b id="total">—</b></div><div class="stat"><span>稼働中</span><b id="online">—</b></div>
<div class="stat"><span>停止中</span><b id="offline">—</b></div><div class="stat"><span>要確認</span><b id="issues">—</b></div>
</div>
<h2>プロジェクト別ステータス</h2><div id="projects"></div>
<div class="notice" id="notice" hidden></div>
<footer>自動更新：60秒ごと · 表示はRailway APIから取得した状態です。停止中は必ずしも障害を意味しません。</footer>
</main><script>
const $=id=>document.getElementById(id);
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n}
function statusClass(s){return s==="online"?"online":s==="error"?"error":s==="deploying"?"deploying":s==="sleeping"?"sleeping":""}
function statusLabel(s){return ({online:"稼働中",offline:"停止中",error:"障害",deploying:"デプロイ中",sleeping:"スリープ",unknown:"不明"})[s]||"不明"}
function render(data){
 const all=data.projects.flatMap(p=>p.services), total=all.length;
 const online=all.filter(s=>s.state==="online").length, errors=all.filter(s=>s.state==="error").length;
 const deploying=all.filter(s=>s.state==="deploying").length, sleeping=all.filter(s=>s.state==="sleeping").length;
 const offline=all.filter(s=>s.state==="offline"||s.state==="unknown").length;
 $("total").textContent=total;$("online").textContent=online;$("offline").textContent=offline;$("issues").textContent=errors+deploying;
 const box=$("overall");box.className="overview"+(errors?" bad":deploying?" warn":"");
 $("headline").textContent=errors?"一部サービスで障害を検知":deploying?"デプロイが進行中":offline===total&&total?"すべてのサービスが停止中":offline?"一部サービスが停止中":"すべて正常に稼働中";
 $("summary").textContent=online+" / "+total+" サービスが稼働中"+(sleeping?" · スリープ "+sleeping:"")+(errors?" · 障害 "+errors:"");
 $("updated").textContent="最終更新："+new Date(data.updatedAt).toLocaleString("ja-JP");
 const root=$("projects");root.replaceChildren();
 for(const p of data.projects){const card=el("section","project"),head=el("div","project-head"),title=el("h3","",p.name),count=el("div","count",p.services.length+" services");
 head.append(title,count);card.append(head);
 if(!p.services.length)card.append(el("div","empty","サービスは登録されていません。"));
 for(const s of p.services){const row=el("div","service"),name=el("div","service-name",s.name),pill=el("span","pill "+statusClass(s.state),statusLabel(s.state));row.append(name,pill);card.append(row)}
 root.append(card)}
 $("notice").hidden=!data.notice;$("notice").textContent=data.notice||"";
}
async function refresh(){try{const r=await fetch("/api/status",{cache:"no-store"});const data=await r.json();if(!r.ok)throw new Error(data.error||"status unavailable");render(data)}catch(e){$("headline").textContent="状態を取得できません";$("summary").textContent="しばらくしてから再読み込みしてください。";$("updated").textContent="更新に失敗";}}
refresh();setInterval(refresh,60000);
</script></body></html>"""

async def gql(client: httpx.AsyncClient, query: str, variables: dict | None = None):
    response = await client.post(
        API_URL,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        json={"query": query, "variables": variables or {}},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if payload.get("errors"):
        raise RuntimeError("Railway API query failed")
    return payload.get("data") or {}

async def fetch_status():
    if not TOKEN:
        return {
            "updatedAt": datetime.now(timezone.utc).isoformat(),
            "projects": [],
            "notice": "管理者による初期設定が必要です。RAILWAY_TOKEN をRailwayの環境変数に設定してください。",
        }

    async with httpx.AsyncClient() as client:
        data = await gql(
            client,
            """query workspaceProjects($workspaceId: String!) {
              projects(workspaceId: $workspaceId) {
                edges { node {
                  id name
                  services { edges { node { id name } } }
                  environments { edges { node { id name } } }
                } }
              }
            }""",
            {"workspaceId": WORKSPACE_ID},
        )
        projects = [edge["node"] for edge in data.get("projects", {}).get("edges", [])]
        sem = asyncio.Semaphore(6)

        async def service_status(project, service, environment):
            async with sem:
                try:
                    result = await gql(
                        client,
                        """query serviceInstance($serviceId: String!, $environmentId: String!) {
                          serviceInstance(serviceId: $serviceId, environmentId: $environmentId) {
                            serviceName latestDeployment { status createdAt }
                          }
                        }""",
                        {"serviceId": service["id"], "environmentId": environment["id"]},
                    )
                    instance = result.get("serviceInstance") or {}
                    deployment = instance.get("latestDeployment") or {}
                    raw = deployment.get("status", "OFFLINE")
                    state = {
                        "SUCCESS": "online",
                        "SLEEPING": "sleeping",
                        "BUILDING": "deploying",
                        "DEPLOYING": "deploying",
                        "INITIALIZING": "deploying",
                        "QUEUED": "deploying",
                        "WAITING": "deploying",
                        "NEEDS_APPROVAL": "deploying",
                        "FAILED": "error",
                        "CRASHED": "error",
                        "THROTTLED": "error",
                    }.get(raw, "offline")
                    return {"name": service["name"], "state": state}
                except Exception:
                    return {"name": service["name"], "state": "unknown"}

        output = []
        for project in projects:
            envs = project.get("environments", {}).get("edges", [])
            environment = next((e["node"] for e in envs if e["node"]["name"].lower() == "production"), None)
            if environment is None and envs:
                environment = envs[0]["node"]
            services = [e["node"] for e in project.get("services", {}).get("edges", [])]
            if environment:
                statuses = await asyncio.gather(*(service_status(project, s, environment) for s in services))
            else:
                statuses = [{"name": s["name"], "state": "unknown"} for s in services]
            output.append({"name": project["name"], "services": sorted(statuses, key=lambda s: s["name"].lower())})

    return {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "projects": sorted(output, key=lambda p: p["name"].lower()),
        "notice": None,
    }

@app.get("/", response_class=HTMLResponse)
async def home():
    return HTMLResponse(PAGE)

@app.get("/api/status")
async def status():
    now = time.monotonic()
    if _cache["data"] is not None and now - _cache["at"] < CACHE_SECONDS:
        return JSONResponse(_cache["data"])
    async with _lock:
        now = time.monotonic()
        if _cache["data"] is not None and now - _cache["at"] < CACHE_SECONDS:
            return JSONResponse(_cache["data"])
        try:
            result = await fetch_status()
            _cache.update(at=time.monotonic(), data=result)
            return JSONResponse(result)
        except Exception:
            if _cache["data"] is not None:
                stale = dict(_cache["data"])
                stale["notice"] = "最新情報の取得に失敗したため、直前の取得結果を表示しています。"
                return JSONResponse(stale)
            return JSONResponse({"error": "status temporarily unavailable"}, status_code=503)

@app.get("/healthz")
async def health():
    return {"ok": True}
