import asyncio
import os
import time
from datetime import datetime, timezone, timedelta

import httpx
import asyncpg
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

API_URL = "https://backboard.railway.com/graphql/v2"
TOKEN = os.getenv("RAILWAY_TOKEN", "")
WORKSPACE_ID = os.getenv("RAILWAY_WORKSPACE_ID", "d72e603c-7a51-417e-984a-35edeb307cbf")
CACHE_SECONDS = int(os.getenv("CACHE_SECONDS", "60"))
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")
MAINTENANCE_MODE = os.getenv("MAINTENANCE_MODE", "false").lower() == "true"
MAINTENANCE_MESSAGE = os.getenv("MAINTENANCE_MESSAGE", "現在メンテナンスを実施しています。")
MAINTENANCE_START = os.getenv("MAINTENANCE_START", "")
MAINTENANCE_END = os.getenv("MAINTENANCE_END", "")

app = FastAPI(title="MAKUMAKUBOT Status")
_cache = {"at": 0.0, "data": None}
_lock = asyncio.Lock()
_db_pool = None
_monitor_task = None

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
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:11px;margin:0 0 16px}.stat{padding:14px 15px;border:1px solid var(--line);background:#fff;border-radius:16px;box-shadow:0 3px 10px #b9686010}.stat span{display:block;color:var(--muted);font-size:11px}.stat b{font-size:27px;color:var(--navy);font-weight:800}.legend{display:flex;flex-wrap:wrap;gap:8px 15px;padding:11px 13px;margin-bottom:25px;border-radius:13px;background:#fff7f3;border:1px solid #f7e5df}.legend-item{display:flex;align-items:center;gap:6px;font-size:11px;color:#626b7d}.legend-dot{width:9px;height:9px;border-radius:50%;flex:none}.section-note{font-size:12px;color:var(--muted);margin:-5px 0 12px}.project-meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.project-status{font-size:10px;color:#647084;background:#f6f7f9;border-radius:99px;padding:3px 8px}.service{padding:13px 1px}.service-name{font-size:14px}.history{margin-top:3px;padding:8px 10px;background:#fbf8f6;border-radius:10px}.history-title{font-size:11px}.event{font-size:11px}.no-events{font-size:11px}
h2{font-size:17px;color:var(--navy);margin:25px 0 10px;display:flex;align-items:center;gap:9px}h2:before{content:"";width:5px;height:18px;background:var(--coral);border-radius:8px}
.project{border:1px solid var(--line);background:#fff;border-radius:17px;padding:16px 18px;margin:10px 0;transition:transform .2s,box-shadow .2s}.project:hover{transform:translateY(-2px);box-shadow:0 8px 20px #bd6c6016}.project-head{display:flex;justify-content:space-between;gap:12px;align-items:center;margin-bottom:8px}.project h3{margin:0;font-size:15px;color:var(--navy)}.count{font-size:11px;color:var(--muted);background:#fff2ed;padding:3px 9px;border-radius:99px}
.service{display:grid;grid-template-columns:minmax(0,1fr) auto;align-items:center;gap:7px 14px;padding:12px 1px;border-top:1px solid #f7e9e4}.service-name{font-weight:600;overflow-wrap:anywhere;font-size:14px}.service-track{grid-column:1/-1;height:16px;border-radius:99px;background:#f4e9e6;overflow:hidden;position:relative;box-shadow:inset 0 1px 3px #26334b12}.service-fill{height:100%;width:100%;border-radius:99px;background:var(--bar);transition:background-color .35s ease;box-shadow:0 0 12px color-mix(in srgb,var(--bar) 32%,transparent)}.history{grid-column:1/-1;padding:2px 0 5px 2px}.history-title{font-size:10px;color:var(--muted);font-weight:700;margin-bottom:4px}.event{display:flex;gap:8px;align-items:baseline;font-size:11px;color:var(--muted);padding:2px 0}.event time{font-variant-numeric:tabular-nums;white-space:nowrap}.event b{font-weight:650;color:var(--ink)}.no-events{font-size:10px;color:#aaa}.service-fill.deploying{background:linear-gradient(90deg,#f2bd58 0%,#ffe2a3 50%,#f2bd58 100%);background-size:200% 100%;animation:barflow 1.8s linear infinite}@keyframes barflow{to{background-position:200% 0}}.pill{white-space:nowrap;font-size:11px;font-weight:700;padding:4px 10px;border-radius:99px;background:#f2f1f2;color:#777}.pill.online{background:#e5f5ed;color:#218c67}.pill.error{background:#fde9eb;color:#c44552}.pill.deploying{background:#fff2d9;color:#9b681e}.pill.sleeping{background:#eaf1ff;color:#315fbd}
.empty,.notice{color:var(--muted);font-size:12px}.notice{border:1px solid var(--line);border-radius:12px;padding:12px;margin-top:16px;background:#fff8f4}.maintenance{display:none;border:1px solid #e7c77d;background:#fff5d9;color:#77551c;border-radius:14px;padding:13px 16px;margin:0 0 15px;font-size:13px}.maintenance.show{display:block}.maintenance b{display:block;font-size:14px;margin-bottom:2px}.uptime{font-size:10px;color:#69758a;display:flex;gap:10px;flex-wrap:wrap}.latency-label{font-size:10px;color:#657087;font-variant-numeric:tabular-nums}.service-track{position:relative}.service-track:after{content:attr(data-latency);position:absolute;inset:0;display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:800;color:#24334a;text-shadow:0 1px 2px #fff9}
footer{text-align:center;margin-top:23px;color:#fff8f2;font-size:11px;text-shadow:0 1px 6px #d95f6060}
@media(max-width:620px){main{padding:22px 13px 40px}.hero{padding:23px 0 18px}.mascot{width:98px;height:98px}.content{padding:16px;border-radius:22px}.stats{grid-template-columns:repeat(2,1fr)}.overview{padding:15px}.project{padding:13px 14px}}
@media(prefers-reduced-motion:reduce){*,*:before,*:after{animation-duration:.01ms!important;animation-iteration-count:1!important;scroll-behavior:auto!important;transition:none!important}}
</style></head><body>
<div class="sky" aria-hidden="true"><div class="cloud c1"></div><div class="cloud c2"></div><div class="cloud c3"></div><span class="star s1">✦</span><span class="star s2">✧</span><span class="star s3">✦</span><span class="star s4">✧</span><i class="spark p1"></i><i class="spark p2"></i><i class="spark p3"></i><i class="spark p4"></i><i class="shooting"></i></div>
<main>
<div class="top"><div class="brand">MAKUMAKUBOT / STATUS</div><div class="updated" id="updated">状態を取得しています…</div></div>
<header class="hero"><h1>サービス稼働状況</h1></header>
<section class="content">
<div class="overview" id="overall"><i class="pulse"></i><div><strong id="headline">状態を確認中</strong><small id="summary">最新の情報を取得しています。</small></div></div>
<div class="stats"><div class="stat"><span>総サービス数</span><b id="total">—</b></div><div class="stat"><span>稼働中</span><b id="online">—</b></div><div class="stat"><span>停止中</span><b id="offline">—</b></div><div class="stat"><span>要確認</span><b id="issues">—</b></div></div>
<div id="maintenance" class="maintenance" role="status"><b>メンテナンス情報</b><span id="maintenanceText"></span></div><div class="legend" aria-label="ステータスの色の説明"><div class="legend-item"><i class="legend-dot" style="background:#218c67"></i>稼働中</div><div class="legend-item"><i class="legend-dot" style="background:#b9b4b5"></i>停止・不明</div><div class="legend-item"><i class="legend-dot" style="background:#d94e5c"></i>障害</div><div class="legend-item"><i class="legend-dot" style="background:#e1a83f"></i>デプロイ中</div><div class="legend-item"><i class="legend-dot" style="background:#648bd0"></i>スリープ</div></div><h2>プロジェクト別ステータス</h2><p class="section-note">各サービスの現在の状態と、直近の状態変化を確認できます。</p><div id="projects"></div><div class="notice" id="notice" hidden></div>
</section><footer>自動更新：60秒ごと · Powered by Railway</footer>
</main><script>
const $=id=>document.getElementById(id);
function el(tag,cls,text){const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n}
function statusClass(s){return s==="online"?"online":s==="error"?"error":s==="deploying"?"deploying":s==="sleeping"?"sleeping":""}
function statusLabel(s){return ({online:"稼働中",offline:"停止中",error:"障害",deploying:"デプロイ中",sleeping:"スリープ",unknown:"不明"})[s]||"不明"}
function render(data,events=[],uptime={}){
 const all=data.projects.flatMap(p=>p.services),total=all.length,online=all.filter(s=>s.state==="online").length,errors=all.filter(s=>s.state==="error").length,deploying=all.filter(s=>s.state==="deploying").length,sleeping=all.filter(s=>s.state==="sleeping").length,offline=all.filter(s=>s.state==="offline").length,unknown=all.filter(s=>s.state==="unknown").length;
 $("total").textContent=total;$("online").textContent=online;$("offline").textContent=offline;$("issues").textContent=errors+unknown;
 const box=$("overall");box.className="overview"+(errors?" bad":deploying?" warn":"");
 $("headline").textContent=errors?"一部サービスで障害を検知":deploying?"デプロイが進行中":offline===total&&total?"すべてのサービスが停止中":offline?"一部サービスが停止中":"すべて正常に稼働中";
 $("summary").textContent="稼働中 "+online+"件 ／ 停止中 "+offline+"件 ／ 障害 "+errors+"件 ／ デプロイ中 "+deploying+"件"+(sleeping?" ／ スリープ "+sleeping+"件":"")+(unknown?" ／ 不明 "+unknown+"件":"");
 $("updated").textContent="最終更新："+new Date(data.updatedAt).toLocaleString("ja-JP");
 const root=$("projects");root.replaceChildren();const byService={};for(const ev of events){(byService[ev.service_id]??=[]).push(ev)}
 for(const p of data.projects){const card=el("section","project"),head=el("div","project-head"),title=el("h3","",p.name),meta=el("div","project-meta"),count=el("div","count","全 "+p.services.length+" サービス"),active=el("div","project-status","稼働 "+p.services.filter(s=>s.state==="online").length);meta.append(count,active);head.append(title,meta);card.append(head);
 if(!p.services.length)card.append(el("div","empty","サービスは登録されていません。"));
 for(const s of p.services){const row=el("div","service"),name=el("div","service-name",s.name),pill=el("span","pill "+statusClass(s.state),statusLabel(s.state)),track=el("div","service-track"),fill=el("div","service-fill "+(s.state==="deploying"?"deploying":""));const bars={online:"#218c67",sleeping:"#648bd0",deploying:"#e1a83f",error:"#d94e5c",offline:"#b9b4b5",unknown:"#b9b4b5"};const color=bars[s.state]||bars.unknown;fill.style.setProperty("--bar",color);track.append(fill);row.append(name,pill,track);const history=el("div","history"),historyTitle=el("div","history-title","稼働率・応答速度・最近の状態変化");history.append(historyTitle);const rates=uptime[s.id]||{};history.append(el("div","uptime","稼働率 24時間 "+(rates["24h"]??"—")+"% ／ 7日 "+(rates["7d"]??"—")+"% ／ 30日 "+(rates["30d"]??"—")+"%"));history.append(el("div","latency-label",s.response_ms==null?"応答速度：計測不可":"応答速度："+s.response_ms+" ms"));track.dataset.latency=s.response_ms==null?"":s.response_ms+" ms";if(s.response_ms!=null){const score=Math.max(8,Math.min(100,100-s.response_ms/20));fill.style.width=score+"%";}else{fill.style.width="100%";}const logs=byService[s.id]||[];if(!logs.length)history.append(el("div","no-events","状態変化の記録はまだありません"));for(const ev of logs.slice(0,3)){const line=el("div","event"),when=el("time","",new Date(ev.created_at).toLocaleString("ja-JP")),what=el("b","",ev.message);line.append(when,what);history.append(line)}row.append(history);card.append(row)}root.append(card)}
 $("notice").hidden=!data.notice;$("notice").textContent=data.notice||"";const m=$("maintenance");m.className="maintenance"+(data.maintenance?.active?" show":"");$("maintenanceText").textContent=data.maintenance?.message||"";
}
async function refresh(){try{const [r,er,ur]=await Promise.all([fetch("/api/status",{cache:"no-store"}),fetch("/api/events",{cache:"no-store"}),fetch("/api/uptime",{cache:"no-store"})]);const data=await r.json(),eventData=await er.json(),ud=await ur.json();if(!r.ok)throw new Error(data.error||"status unavailable");render(data,eventData.events||[],ud.uptime||{})}catch(e){$("headline").textContent="状態を取得できません";$("summary").textContent="しばらくしてから再読み込みしてください。";$("updated").textContent="更新に失敗"}}
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
                            serviceName latestDeployment { status createdAt } domains { serviceDomains { domain } customDomains { domain } }
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
                    domain_items=(instance.get("domains") or {}).get("serviceDomains", []) + (instance.get("domains") or {}).get("customDomains", [])
                    domain=next((x.get("domain") for x in domain_items if x.get("domain")), None)
                    latency=None
                    if domain and state == "online":
                        try:
                            started=time.perf_counter()
                            await client.get("https://"+domain,timeout=5.0,follow_redirects=True)
                            latency=round((time.perf_counter()-started)*1000)
                        except Exception:
                            latency=None
                    return {"id": service["id"], "name": service["name"], "state": state, "response_ms": latency}
                except Exception:
                    return {"id": service["id"], "name": service["name"], "state": "unknown", "response_ms": None}

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
                statuses = [{"id": s["id"], "name": s["name"], "state": "unknown", "response_ms": None} for s in services]
            output.append({"name": project["name"], "services": sorted(statuses, key=lambda s: s["name"].lower())})

    return {
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "projects": sorted(output, key=lambda p: p["name"].lower()),
        "notice": None,
        "maintenance": {"active": MAINTENANCE_MODE, "message": MAINTENANCE_MESSAGE + ((" · 予定："+MAINTENANCE_START+" ～ "+MAINTENANCE_END) if MAINTENANCE_START or MAINTENANCE_END else "")},
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


async def persist_events(data):
    if _db_pool is None or data.get("notice"):
        return
    async with _db_pool.acquire() as conn:
        for project in data.get("projects", []):
            for service in project.get("services", []):
                row = await conn.fetchrow(
                    "SELECT state FROM service_states WHERE service_id=$1",
                    service["id"],
                )
                await conn.execute("INSERT INTO service_samples(service_id,state,response_ms) VALUES($1,$2,$3)", service["id"], service["state"], service.get("response_ms"))
                if row is None:
                    await conn.execute(
                        "INSERT INTO service_states(service_id, project_name, service_name, state, updated_at) VALUES($1,$2,$3,$4,NOW())",
                        service["id"], project["name"], service["name"], service["state"],
                    )
                elif row["state"] != service["state"]:
                    old, new = row["state"], service["state"]
                    labels = {"online":"稼働中","offline":"停止中","error":"障害","deploying":"デプロイ中","sleeping":"スリープ","unknown":"状態不明"}
                    if new == "online" and old in ("offline", "error", "unknown"):
                        failure = await conn.fetchrow("SELECT created_at FROM service_events WHERE service_id=$1 AND new_state IN ('offline','error') ORDER BY created_at DESC LIMIT 1", service["id"])
                        duration = ""
                        if failure:
                            seconds=max(0,int((datetime.now(timezone.utc)-failure["created_at"]).total_seconds()))
                            duration=f"（復旧まで {seconds//3600}時間{(seconds%3600)//60}分）"
                        message = "復旧を検知"+duration
                    elif new in ("offline", "error"):
                        message = "停止・障害を検知"
                    else:
                        message = labels.get(old, old) + " → " + labels.get(new, new)
                    await conn.execute(
                        "INSERT INTO service_events(service_id, project_name, service_name, previous_state, new_state, message) VALUES($1,$2,$3,$4,$5,$6)",
                        service["id"], project["name"], service["name"], old, new, message,
                    )
                    await conn.execute(
                        "UPDATE service_states SET project_name=$2, service_name=$3, state=$4, updated_at=NOW() WHERE service_id=$1",
                        service["id"], project["name"], service["name"], new,
                    )
                    if new in ("offline", "error", "online"):
                        await send_discord_notice(project["name"], service["name"], message)

async def send_discord_notice(project_name, service_name, message):
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            await client.post(DISCORD_WEBHOOK_URL, json={"content": f"【MAKUMAKUBOT Status】\\n{project_name} / {service_name}\\n{message}"})
    except Exception:
        pass

async def monitor_loop():
    while True:
        try:
            result = await fetch_status()
            await persist_events(result)
            _cache.update(at=time.monotonic(), data=result)
        except Exception:
            pass
        await asyncio.sleep(CACHE_SECONDS)

@app.on_event("startup")
async def startup():
    global _db_pool, _monitor_task
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        for attempt in range(12):
            try:
                _db_pool = await asyncpg.create_pool(database_url, min_size=1, max_size=4, command_timeout=15)
                async with _db_pool.acquire() as conn:
                    await conn.execute("""
                        CREATE TABLE IF NOT EXISTS service_states (
                            service_id TEXT PRIMARY KEY,
                            project_name TEXT NOT NULL,
                            service_name TEXT NOT NULL,
                            state TEXT NOT NULL,
                            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        );
                        CREATE TABLE IF NOT EXISTS service_events (
                            id BIGSERIAL PRIMARY KEY,
                            service_id TEXT NOT NULL,
                            project_name TEXT NOT NULL,
                            service_name TEXT NOT NULL,
                            previous_state TEXT NOT NULL,
                            new_state TEXT NOT NULL,
                            message TEXT NOT NULL,
                            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                        );
                        CREATE INDEX IF NOT EXISTS service_events_created_idx ON service_events(created_at DESC);
                        CREATE TABLE IF NOT EXISTS service_samples (id BIGSERIAL PRIMARY KEY, service_id TEXT NOT NULL, state TEXT NOT NULL, response_ms INTEGER, sampled_at TIMESTAMPTZ NOT NULL DEFAULT NOW());
                        CREATE INDEX IF NOT EXISTS service_samples_service_time_idx ON service_samples(service_id, sampled_at DESC);
                    """)
                break
            except Exception:
                if _db_pool:
                    await _db_pool.close()
                    _db_pool = None
                await asyncio.sleep(5)
    _monitor_task = asyncio.create_task(monitor_loop())

@app.on_event("shutdown")
async def shutdown():
    if _monitor_task:
        _monitor_task.cancel()
    if _db_pool:
        await _db_pool.close()

@app.get("/api/uptime")
async def uptime():
    if _db_pool is None:
        return JSONResponse({"uptime": {}})
    now=datetime.now(timezone.utc)
    result={}
    async with _db_pool.acquire() as conn:
        ids=await conn.fetch("SELECT DISTINCT service_id FROM service_samples")
        for item in ids:
            samples=await conn.fetch("SELECT state,sampled_at FROM service_samples WHERE service_id=$1 AND sampled_at >= NOW()-INTERVAL '30 days' ORDER BY sampled_at",item["service_id"])
            if not samples:
                continue
            values={}
            for key,days in (("24h",1),("7d",7),("30d",30)):
                first=max(now-timedelta(days=days),samples[0]["sampled_at"])
                covered=max(0,(now-first).total_seconds())
                up=0.0
                for i,sample in enumerate(samples):
                    a=max(first,sample["sampled_at"])
                    b=min(now,samples[i+1]["sampled_at"] if i+1<len(samples) else now)
                    if b>a and sample["state"]=="online": up+=(b-a).total_seconds()
                values[key]=round(up/covered*100,2) if covered>0 else None
            result[item["service_id"]]=values
    return JSONResponse({"uptime": result})

@app.get("/api/events")
async def events():
    if _db_pool is None:
        return JSONResponse({"events": [], "notice": "履歴データベースに接続できません"})
    async with _db_pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT service_id, project_name, service_name, previous_state, new_state, message, created_at
            FROM service_events ORDER BY created_at DESC LIMIT 150
        """)
    return JSONResponse({"events": [
        {"service_id": r["service_id"], "project_name": r["project_name"],
         "service_name": r["service_name"], "previous_state": r["previous_state"],
         "new_state": r["new_state"], "message": r["message"],
         "created_at": r["created_at"].isoformat()}
        for r in rows
    ]})

@app.get("/healthz")
async def health():
    return {"ok": True}
