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
<meta name="theme-color" content="#ff817b"><title>MAKUMAKUBOT Status</title>
<style>
:root{color-scheme:light;--coral:#ff817b;--coral-deep:#f36c70;--pink:#ffd9d0;--navy:#142b4e;--ink:#25334b;--muted:#7d8294;--paper:#fffdf9;--line:#f2d8d2;--green:#218c67;--red:#d94e5c;--yellow:#a66b17;--blue:#315fbd}
*{box-sizing:border-box}html{min-height:100%;background:#ff8a83}body{margin:0;min-height:100vh;overflow-x:hidden;color:var(--ink);font:15px/1.6 system-ui,-apple-system,"Segoe UI",sans-serif;background:linear-gradient(145deg,#ffaaa0 0%,#ff817b 46%,#f46d73 100%);position:relative}
.sky{position:fixed;inset:0;overflow:hidden;pointer-events:none;z-index:0}
.cloud{position:absolute;width:240px;height:90px;border-radius:70px;background:#fff0e8;opacity:.56;filter:blur(.2px);animation:drift 26s ease-in-out infinite alternate}
.cloud:before,.cloud:after{content:"";position:absolute;background:inherit;border-radius:50%}.cloud:before{width:112px;height:112px;left:34px;top:-47px}.cloud:after{width:135px;height:135px;right:25px;top:-62px}
.c1{left:-85px;top:13%;transform:scale(1.25);animation-duration:32s}.c2{right:-125px;top:56%;transform:scale(1.5);animation-duration:38s}.c3{left:14%;bottom:-58px;transform:scale(1.1);animation-duration:29s}
.star{position:absolute;color:#fff3df;font-size:27px;text-shadow:0 2px 12px #fff5;animation:twinkle 3.8s ease-in-out infinite}.s1{left:11%;top:19%}.s2{right:13%;top:30%;animation-delay:1s}.s3{left:78%;top:76%;animation-delay:2s}.s4{left:34%;top:87%;font-size:20px;animation-delay:.6s}
.spark{position:absolute;width:7px;height:7px;border-radius:50%;background:#fff2e7;animation:twinkle 4.2s infinite}.p1{left:30%;top:10%}.p2{right:27%;top:17%;animation-delay:1.2s}.p3{left:7%;top:69%;animation-delay:2.1s}.p4{right:8%;bottom:12%;animation-delay:.4s}
.shooting{position:absolute;width:190px;height:10px;border-radius:99px;background:linear-gradient(90deg,#fff0e8,transparent);transform:rotate(-42deg);right:8%;top:12%;opacity:.7;animation:shoot 9s ease-in-out infinite}
@keyframes drift{from{translate:-14px 0}to{translate:30px -16px}}@keyframes twinkle{0%,100%{opacity:.55;scale:.85}50%{opacity:1;scale:1.16}}@keyframes shoot{0%,72%,100%{translate:0 0;opacity:0}76%{opacity:.8}88%{translate:-160px 120px;opacity:0}}
main{position:relative;z-index:1;max-width:1000px;margin:0 auto;padding:34px 22px 58px}
.top{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap}.brand{font-size:12px;letter-spacing:.16em;color:#fff;font-weight:850;text-shadow:0 1px 8px #d85d5d66}.updated{color:#fff8f2;font-size:12px;text-shadow:0 1px 6px #d85d5d66}
.hero{text-align:center;padding:30px 0 22px}.mascot{width:118px;height:118px;margin:0 auto 10px;display:grid;place-items:center;filter:drop-shadow(0 10px 15px #b94e4e35);animation:bob 4.5s ease-in-out infinite}
.mascot svg{width:100%;height:100%}@keyframes bob{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-8px) rotate(2deg)}}
h1{font-size:clamp(29px,5vw,43px);letter-spacing:-.045em;color:#fff;margin:0 0 4px;text-shadow:0 2px 12px #d95f6060}.sub{color:#fff5ef;margin:0;font-size:14px;text-shadow:0 1px 6px #d95f6060}
.content{background:var(--paper);border:1px solid #fff9;border-radius:28px;padding:25px;box-shadow:0 18px 55px #a8444830;animation:rise .7s cubic-bezier(.2,.8,.2,1) both}@keyframes rise{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
.overview{border:1px solid var(--line);background:linear-gradient(110deg,#fff3ed,#fffaf6);border-radius:19px;padding:18px 20px;display:flex;align-items:center;gap:15px;margin-bottom:16px}
.pulse{width:13px;height:13px;border-radius:50%;background:var(--green);box-shadow:0 0 0 6px #218c6719;flex:none;animation:pulse 2.2s infinite}.overview.bad .pulse{background:var(--red);box-shadow:0 0 0 6px #d94e5c19}.overview.warn .pulse{background:var(--yellow);box-shadow:0 0 0 6px #a66b1719}@keyframes pulse{50%{box-shadow:0 0 0 10px transparent}}
.overview strong{font-size:18px;display:block;color:var(--navy)}.overview small{color:var(--muted)}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:11px;margin:0 0 27px}.stat{padding:14px 15px;border:1px solid var(--line);background:#fff;border-radius:16px;box-shadow:0 3px 10px #b9686010}.stat span{display:block;color:var(--muted);font-size:11px}.stat b{font-size:27px;color:var(--navy);font-weight:800}
h2{font-size:17px;color:var(--navy);margin:25px 0 10px;display:flex;align-items:center;gap:9px}h2:before{content:"";width:5px;height:18px;background:var(--coral);border-radius:8px}
.project{border:1px solid var(--line);background:#fff;border-radius:17px;padding:16px 18px;margin:10px 0;transition:transform .2s,box-shadow .2s}.project:hover{transform:translateY(-2px);box-shadow:0 8px 20px #bd6c6016}.project-head{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:8px}.project h3{margin:0;font-size:15px;color:var(--navy)}.count{font-size:11px;color:var(--muted);background:#fff2ed;padding:3px 9px;border-radius:99px}
.service{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px 1px;border-top:1px solid #f7e9e4}.service-name{font-weight:550;overflow-wrap:anywhere;font-size:14px}.pill{white-space:nowrap;font-size:11px;font-weight:700;padding:4px 10px;border-radius:99px;background:#f2f1f2;color:#777}.pill.online{background:#e5f5ed;color:#218c67}.pill.error{background:#fde9eb;color:#c44552}.pill.deploying{background:#fff2d9;color:#9b681e}.pill.sleeping{background:#eaf1ff;color:#315fbd}
.empty,.notice{color:var(--muted);font-size:12px}.notice{border:1px solid var(--line);border-radius:12px;padding:12px;margin-top:16px;background:#fff8f4}
footer{text-align:center;margin-top:23px;color:#fff8f2;font-size:11px;text-shadow:0 1px 6px #d95f6060}
@media(max-width:620px){main{padding:22px 13px 40px}.hero{padding:23px 0 18px}.mascot{width:98px;height:98px}.content{padding:16px;border-radius:22px}.stats{grid-template-columns:repeat(2,1fr)}.overview{padding:15px}.project{padding:13px 14px}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation-duration:.01ms!important;animation-iteration-count:1!important;scroll-behavior:auto!important;transition:none!important}}
</style></head><body>
<div class="sky" aria-hidden="true"><div class="cloud c1"></div><div class="cloud c2"></div><div class="cloud c3"></div><span class="star s1">✦</span><span class="star s2">✧</span><span class="star s3">✦</span><span class="star s4">✧</span><i class="spark p1"></i><i class="spark p2"></i><i class="spark p3"></i><i class="spark p4"></i><i class="shooting"></i></div>
<main>
<div class="top"><div class="brand">MAKUMAKUBOT / STATUS</div><div class="updated" id="updated">状態を取得しています…</div></div>
<header class="hero"><div class="mascot" aria-hidden="true"><svg viewBox="0 0 120 120" xmlns="http://www.w3.org/2000/svg"><path d="M15 48 18 12 45 32Q60 25 75 32L102 12 105 49Q116 62 109 83 99 111 60 112 21 111 11 83 4 62 15 48Z" fill="#ff817b"/><path d="M24 49 25 24 43 39Q60 32 77 39L95 24 96 50Q105 63 99 82 91 103 60 104 29 103 21 82 15 63 24 49Z" fill="#fffdf9"/><path d="M28 47 28 30 43 42Z M92 47 92 30 77 42Z" fill="#142b4e"/><ellipse cx="43" cy="65" rx="10" ry="14" fill="#2468d9"/><ellipse cx="77" cy="65" rx="10" ry="14" fill="#2468d9"/><circle cx="46" cy="60" r="4" fill="white"/><circle cx="80" cy="60" r="4" fill="white"/><path d="M54 79Q60 74 66 79L60 85Z" fill="#142b4e"/><path d="M60 85Q53 94 45 87M60 85Q67 94 75 87" fill="none" stroke="#142b4e" stroke-width="3" stroke-linecap="round"/><path d="M33 80 12 76M34 88 13 93M87 80 108 76M86 88 107 93" stroke="#142b4e" stroke-width="3" stroke-linecap="round"/></svg></div><h1>サービス稼働状況</h1><p class="sub">今日も、みんな元気に動いているかな？</p></header>
<section class="content">
<div class="overview" id="overall"><i class="pulse"></i><div><strong id="headline">状態を確認中</strong><small id="summary">最新の情報を取得しています。</small></div></div>
<div class="stats"><div class="stat"><span>総サービス数</span><b id="total">—</b></div><div class="stat"><span>稼働中</span><b id="online">—</b></div><div class="stat"><span>停止中</span><b id="offline">—</b></div><div class="stat"><span>要確認</span><b id="issues">—</b></div></div>
<h2>プロジェクト別ステータス</h2><div id="projects"></div><div class="notice" id="notice" hidden></div>
</section><footer>自動更新：60秒ごと · Powered by Railway</footer>
</main><script>
const $=id=>document.getElementById(id);
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n}
function statusClass(s){return s==="online"?"online":s==="error"?"error":s==="deploying"?"deploying":s==="sleeping"?"sleeping":""}
function statusLabel(s){return ({online:"稼働中",offline:"停止中",error:"障害",deploying:"デプロイ中",sleeping:"スリープ",unknown:"不明"})[s]||"不明"}
function render(data){
 const all=data.projects.flatMap(p=>p.services),total=all.length,online=all.filter(s=>s.state==="online").length,errors=all.filter(s=>s.state==="error").length,deploying=all.filter(s=>s.state==="deploying").length,sleeping=all.filter(s=>s.state==="sleeping").length,offline=all.filter(s=>s.state==="offline"||s.state==="unknown").length;
 $("total").textContent=total;$("online").textContent=online;$("offline").textContent=offline;$("issues").textContent=errors+deploying;
 const box=$("overall");box.className="overview"+(errors?" bad":deploying?" warn":"");
 $("headline").textContent=errors?"一部サービスで障害を検知":deploying?"デプロイが進行中":offline===total&&total?"すべてのサービスが停止中":offline?"一部サービスが停止中":"すべて正常に稼働中";
 $("summary").textContent=online+" / "+total+" サービスが稼働中"+(sleeping?" · スリープ "+sleeping:"")+(errors?" · 障害 "+errors:"");
 $("updated").textContent="最終更新："+new Date(data.updatedAt).toLocaleString("ja-JP");
 const root=$("projects");root.replaceChildren();
 for(const p of data.projects){const card=el("section","project"),head=el("div","project-head"),title=el("h3","",p.name),count=el("div","count",p.services.length+" services");head.append(title,count);card.append(head);
 if(!p.services.length)card.append(el("div","empty","サービスは登録されていません。"));
 for(const s of p.services){const row=el("div","service"),name=el("div","service-name",s.name),pill=el("span","pill "+statusClass(s.state),statusLabel(s.state));row.append(name,pill);card.append(row)}root.append(card)}
 $("notice").hidden=!data.notice;$("notice").textContent=data.notice||"";
}
async function refresh(){try{const r=await fetch("/api/status",{cache:"no-store"});const data=await r.json();if(!r.ok)throw new Error(data.error||"status unavailable");render(data)}catch(e){$("headline").textContent="状態を取得できません";$("summary").textContent="しばらくしてから再読み込みしてください。";$("updated").textContent="更新に失敗"}}
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
