from aiohttp import web
from web.web_assets import build_page, get_auth, form_wrapper, MAX_WEB_RESULTS
from database.users_chats_db import db as user_db
from utils import temp

dashboard_routes = web.RouteTableDef()

# ─────────────────────────────────────────────────────────────────────────────
# 🎨 NEW CARD UI CSS — With Grouping Components & Shimmer Effect
# ─────────────────────────────────────────────────────────────────────────────
CARD_CSS = """
<style>
/* ── Search zone ── */
.search-zone{padding:16px 20px 0}
.search-row1{display:flex;align-items:center;gap:10px;margin-bottom:10px}
.search-row2{display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:16px}
@media(min-width:768px){
  .search-zone{padding:16px 24px 0;display:flex;align-items:center;gap:10px;flex-wrap:nowrap}
  .search-row1{flex:1;margin-bottom:0}
  .search-row2{margin-bottom:0;justify-content:flex-start;flex-shrink:0}
}
.search-wrap{flex:1;min-width:0;display:flex;align-items:center;background:var(--bg3);border:1.5px solid var(--border);border-radius:12px;padding:0 6px 0 18px;gap:8px;overflow:hidden;min-height:38px;transition:border-color .18s}
.search-wrap:focus-within{border-color:var(--border)}
.search-input{flex:1;min-width:0;width:100%;background:transparent;border:none;outline:none;color:var(--text);caret-color:var(--accent);font-size:14px;font-weight:600;padding:6px 0;font-family:inherit;-webkit-tap-highlight-color:transparent}
.search-input::placeholder{color:var(--muted);font-weight:400}
.search-input:-webkit-autofill,
.search-input:-webkit-autofill:hover,
.search-input:-webkit-autofill:focus,
.search-input:-webkit-autofill:active{
  -webkit-box-shadow:0 0 0 100px var(--bg3) inset !important;
  box-shadow:0 0 0 100px var(--bg3) inset !important;
  -webkit-text-fill-color:var(--text) !important;
  caret-color:var(--accent) !important;
  border-radius:999px;
  transition:background-color 9999s ease-in-out 0s;
}
.search-btn{position:relative;overflow:hidden;flex-shrink:0;background:var(--accent);color:#fff;border:none;border-radius:12px;padding:0 20px;height:38px;font-size:14px;font-weight:700;cursor:pointer;white-space:nowrap;transition:transform .15s,box-shadow .15s,background .15s;letter-spacing:.3px}
.search-btn:hover{background:var(--accent-hover);transform:scale(1.03);box-shadow:0 6px 22px rgba(229,9,20,0.50)}
.search-btn:active{transform:scale(.96)}
.search-btn::after{content:'';position:absolute;inset:0;background:rgba(255,255,255,0);border-radius:inherit;pointer-events:none}
.search-btn.ripple-go::after{animation:btnRipple .45s ease-out forwards}
@keyframes btnRipple{0%{background:rgba(255,255,255,0.28);transform:scale(.6)}100%{background:rgba(255,255,255,0);transform:scale(1.6)}}

.cdd-wrap{flex:0 1 auto;min-width:0;position:relative;user-select:none}
.cdd-btn{width:auto;background:var(--bg3);color:var(--text);border:1.5px solid var(--border);border-radius:999px;padding:8px 28px 8px 14px;font-size:11px;font-weight:700;cursor:pointer;font-family:inherit;box-sizing:border-box;display:inline-flex;align-items:center;gap:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;transition:border-color .15s,box-shadow .15s}
.cdd-btn:hover,.cdd-btn.open{border-color:var(--accent);box-shadow:0 0 0 3px rgba(229,9,20,0.12)}
.cdd-arrow{position:absolute;right:12px;top:50%;transform:translateY(-50%);pointer-events:none;font-size:9px;color:var(--muted);transition:transform .2s}
.cdd-btn.open+.cdd-arrow{transform:translateY(-50%) rotate(180deg)}
.cdd-menu{position:absolute;top:calc(100% + 7px);left:50%;transform:translateX(-50%);min-width:max-content;background:var(--bg2,var(--bg3));border:1.5px solid var(--border);border-radius:16px;overflow:hidden;z-index:9999;box-shadow:0 8px 32px rgba(0,0,0,.45);animation:cddIn .15s ease}
@keyframes cddIn{from{opacity:0;transform:translateY(-6px)}to{opacity:1;transform:translateY(0)}}
.cdd-item{display:flex;align-items:center;gap:10px;padding:13px 14px;font-size:13px;font-weight:700;color:var(--text);cursor:pointer;transition:background .12s;border-bottom:1px solid var(--border)}
.cdd-item:last-child{border-bottom:none}
.cdd-item:hover{background:var(--bg3)}
.cdd-item.selected{color:var(--accent)}
.cdd-radio{width:18px;height:18px;border-radius:50%;border:2px solid var(--border);margin-left:auto;flex-shrink:0;display:flex;align-items:center;justify-content:center;transition:border-color .15s}
.cdd-item.selected .cdd-radio{border-color:var(--accent)}
.cdd-radio-dot{width:8px;height:8px;border-radius:50%;background:var(--accent);display:none}
.cdd-item.selected .cdd-radio-dot{display:block}

.res-grid{display:grid;grid-template-columns:1fr;gap:4px;margin-bottom:24px}
@media(min-width:600px){.res-grid{grid-template-columns:repeat(3,1fr);gap:14px}}
.res-grid.mode-none .poster-box{display:none}

.file-card{background:var(--card);border-radius:6px;overflow:hidden;border:1px solid var(--border);transition:transform .22s cubic-bezier(.4,0,.2,1),box-shadow .22s,border-color .22s;cursor:pointer}
.file-card:hover{transform:translateY(-4px);border-color:rgba(229,9,20,.4);box-shadow:0 14px 36px rgba(0,0,0,.6),0 0 0 1px rgba(229,9,20,.2)}

.poster-box{position:relative;padding-top:56.25%;background:linear-gradient(90deg, var(--bg3) 0px, var(--bg4) 50%, var(--bg3) 100%);background-size:200% 100%;animation:shimmer 1.5s infinite linear;overflow:hidden}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
.fc-poster{position:absolute;inset:0;width:100%;height:100%;object-fit:cover;opacity:0;transition:opacity 0.25s ease-in-out, transform 0.35s ease}
.fc-poster.loaded{opacity:1}
.file-card:hover .fc-poster{transform:scale(1.05)}
.thumb-error{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;background:#1f1f1f;z-index:2}

.poster-top{position:absolute;top:0;left:0;right:0;display:flex;align-items:center;gap:5px;padding:8px;z-index:3}
.type-chip{background:rgba(0,0,0,.72);backdrop-filter:blur(8px);color:#fff;border-radius:5px;padding:3px 8px;font-size:10px;font-weight:800;letter-spacing:.8px;border:1px solid rgba(255,255,255,.14);line-height:1.4}
.size-chip{background:rgba(0,0,0,.60);backdrop-filter:blur(8px);color:#e0e0e0;border-radius:5px;padding:3px 8px;font-size:10px;font-weight:600;border:1px solid rgba(255,255,255,.08);line-height:1.4}
.source-pill{margin-left:auto;border-radius:20px;padding:3px 8px;font-size:9px;font-weight:700;letter-spacing:.4px;display:inline-flex;align-items:center;gap:4px;backdrop-filter:blur(8px)}
.source-pill.primary{background:#14532d;color:#4ade80;border:1px solid #22c55e}
.source-pill.cloud{background:#1e3a5f;color:#93c5fd;border:1px solid #60a5fa}
.source-pill.archive{background:#7c2d12;color:#fdba74;border:1px solid #fb923c}
.source-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0}
.primary .source-dot{background:#22c55e;box-shadow:0 0 4px #22c55e}
.cloud .source-dot{background:#60a5fa;box-shadow:0 0 4px #60a5fa}
.archive .source-dot{background:#fb923c;box-shadow:0 0 4px #fb923c}

.poster-admin{position:absolute;bottom:0;left:0;right:0;display:flex;gap:6px;padding:7px 8px;opacity:0;transform:translateY(8px);transition:opacity .2s ease,transform .22s ease;pointer-events:none;z-index:4}
.file-card.admin-active .poster-admin{opacity:1;transform:translateY(0);pointer-events:all}
.text-admin-row{display:none;gap:5px;padding:5px 11px 0}
.file-card.admin-active .text-admin-row{display:flex}
.btn-edit,.btn-del{flex:1;padding:6px 0;border-radius:6px;font-size:11px;font-weight:700;cursor:pointer;transition:background .12s,transform .1s;border:none}
.btn-edit{background:rgba(42,42,48,.90);backdrop-filter:blur(10px);color:#fff;border:1px solid rgba(255,255,255,.18)}
.btn-edit:hover{background:rgba(80,80,88,.95)}
.btn-edit:active{transform:scale(.93)}
.btn-del{background:rgba(160,8,8,.78);backdrop-filter:blur(10px);color:#fff;border:1px solid rgba(229,9,20,.45)}
.btn-del:hover{background:rgba(229,9,20,.92)}
.btn-del:active{transform:scale(.93)}

.fc-body{padding:10px 11px 12px}
.fc-name{color:var(--text);font-size:12.5px;font-weight:600;line-height:1.45;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;cursor:pointer;transition:color .18s;text-decoration:none}
.fc-name:hover{color:var(--accent);text-decoration:underline;text-decoration-color:var(--accent);text-underline-offset:2px}

.fc-text-info{display:flex;align-items:center;gap:6px;padding:10px 11px 0;flex-wrap:wrap;margin-bottom:4px}
.tc-type{background:var(--bg4);color:var(--muted);border-radius:5px;padding:2px 7px;font-size:9px;font-weight:800;letter-spacing:.8px;border:1px solid var(--border)}
.tc-size{color:var(--muted);font-size:11px}

.pagination{display:flex;align-items:center;justify-content:center;gap:12px;margin-top:8px}
.pg-btn{background:var(--bg4);color:var(--text);border:1px solid var(--border);border-radius:6px;padding:8px 18px;font-size:12px;font-weight:700;cursor:pointer;transition:background .15s,transform .15s,box-shadow .15s}
.pg-btn:disabled{background:var(--bg3);color:var(--muted);cursor:not-allowed;opacity:.45}
.pg-btn:not(:disabled):hover{background:var(--accent);color:#fff;border-color:var(--accent);box-shadow:0 4px 16px rgba(229,9,20,.35)}
.pg-btn:not(:disabled):active{transform:scale(.93);box-shadow:none}
.pg-info{color:var(--muted);font-size:12px;font-weight:600}

.empty{text-align:center;padding:60px 20px;color:var(--muted)}
.empty-icon{font-size:36px;margin-bottom:12px}
.spin-wrap{display:flex;flex-direction:column;align-items:center;gap:16px;padding:60px 20px;color:var(--muted)}
.spinner{width:36px;height:36px;border:3px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

.group-quality-container { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
.q-chip-btn { background:var(--bg4); border:1px solid var(--border); color:var(--text); padding:5px 10px; border-radius:6px; font-size:11px; font-weight:700; cursor:pointer; transition:0.12s; }
.q-chip-btn:hover { border-color:var(--accent); color:var(--accent); background:rgba(229,9,20,0.05); }
</style>
"""

# ─────────────────────────────────────────────────────────────────────────────
# 🎬 JS ENGINE — Fixed String Concatenation & Absolute Cross-Network Isolation
# ─────────────────────────────────────────────────────────────────────────────
JS_ENGINE = """
var curQ='',curOff=0,nextOff='',curCol='all',curPage=1;
var pMode=localStorage.getItem('posterMode')||'tg';
var curViewMode='group'; 
var LIMIT_VAL = __LIMIT_PLACEHOLDER__;

var activeFid = '', activeCol = '', cropperInstance = null;

function closeCdds(){
    document.getElementById('cddColMenu').style.display='none';
    document.getElementById('cddColBtn').classList.remove('open');
    document.getElementById('cddModeMenu').style.display='none';
    document.getElementById('cddModeBtn').classList.remove('open');
    if(document.getElementById('cddViewMenu')) {
        document.getElementById('cddViewMenu').style.display='none';
        document.getElementById('cddViewBtn').classList.remove('open');
    }
}
function toggleCdd(which,e){
    if(e){e.stopPropagation();}
    var menuId='cdd' + which.charAt(0).toUpperCase() + which.slice(1) + 'Menu';
    var btnId='cdd' + which.charAt(0).toUpperCase() + which.slice(1) + 'Btn';
    var menu=document.getElementById(menuId);
    var btn=document.getElementById(btnId);
    var isOpen=menu.style.display!=='none';
    closeCdds();
    if(!isOpen){menu.style.display='block';btn.classList.add('open');}
}
function pickCol(val,label,el,e){
    if(e){e.stopPropagation();}
    curCol=val;
    document.getElementById('cddColLabel').textContent=label;
    document.querySelectorAll('#cddColMenu .cdd-item').forEach(function(i){i.classList.remove('selected');});
    el.classList.add('selected');
    closeCdds();
    if(curQ)doSearch(0);
}
function pickMode(val,label,el,e){
    if(e){e.stopPropagation();}
    pMode=val;
    localStorage.setItem('posterMode',pMode);
    document.getElementById('cddModeLabel').textContent=label;
    document.querySelectorAll('#cddModeMenu .cdd-item').forEach(function(i){i.classList.remove('selected');});
    el.classList.add('selected');
    closeCdds();
    if(curQ)doSearch(curOff);
}
function pickViewMode(val,label,el,e){
    if(e){e.stopPropagation();}
    curViewMode=val;
    document.getElementById('cddViewLabel').textContent=label;
    document.querySelectorAll('#cddViewMenu .cdd-item').forEach(function(i){i.classList.remove('selected');});
    el.classList.add('selected');
    closeCdds();
    if(curQ)doSearch(0);
}

document.addEventListener('click',function(e){
    if(!e.target.closest('.cdd-wrap')){closeCdds();}
});

function handleThumbError(fileId) {
    var img = document.getElementById('img-poster-' + fileId);
    if (img) { img.style.opacity = '0'; }
    var errBox = document.getElementById('thumb-err-' + fileId);
    if (!errBox) {
        var box = document.getElementById('poster-box-' + fileId);
        if (box) {
            var div = document.createElement('div');
            div.id = 'thumb-err-' + fileId;
            div.className = 'thumb-error';
            div.innerHTML = '<span style="font-size:11px;color:var(--muted);">थंबनेल लोड नहीं हुआ</span>';
            box.appendChild(div);
        }
    }
}

async function reloadThumb(fileId, col) {
    var timestamp = new Date().getTime();
    var img = document.getElementById('img-poster-' + fileId);
    if (img) {
        img.src = '/api/thumb?file_id=' + fileId + '&col=' + col + '&retry=true&t=' + timestamp;
        img.classList.remove('loaded');
    }
    var errBox = document.getElementById('thumb-err-' + fileId);
    if (errBox) { errBox.remove(); }
}

function triggerRipple(btn){btn.classList.remove('ripple-go');void btn.offsetWidth;btn.classList.add('ripple-go');setTimeout(function(){btn.classList.remove('ripple-go');},460);}

function toggleAdminBtns(card,e){
    e.stopPropagation();
    var isActive=card.classList.contains('admin-active');
    document.querySelectorAll('.file-card.admin-active').forEach(function(c){c.classList.remove('admin-active');});
    if(!isActive){card.classList.add('admin-active');}
}
document.addEventListener('click',function(){
    document.querySelectorAll('.file-card.admin-active').forEach(function(c){c.classList.remove('admin-active');});
});

async function doSearch(o){
    var q=document.getElementById('q').value.trim();
    if(!q){showToast('Please enter a movie name','error');return;}
    curQ=q;curOff=o;if(o===0)curPage=1;

    var resDiv=document.getElementById('results');
    resDiv.className='res-grid mode-'+pMode;
    resDiv.innerHTML='<div class="spin-wrap"><div class="spinner"></div><span>Searching Matrix...</span></div>';

    try{
        var r=await fetch('/api/search?q='+encodeURIComponent(q)+'&offset='+o+'&col='+curCol+'&mode='+pMode+'&view_mode='+curViewMode);
        if(!r.ok){showToast('Error fetching','error');return;}
        var d=await r.json();
        if(d.error){showToast(d.error,'error');return;}
        document.getElementById('resInfo').style.display='none';
        if(!d.results||!d.results.length){
            resDiv.innerHTML='<div class="empty"><div class="empty-icon">&#9888;</div><p>No titles found for "'+q+'"</p></div>';
            document.getElementById('pageBox').style.display='none';return;
        }

        if(d.is_admin && document.getElementById('cddViewWrap')) {
            document.getElementById('cddViewWrap').style.display = 'block';
        }

        var h='';
        d.results.forEach(function(f){
            var sc=(f.source||'primary').toLowerCase();
            if(!['primary','cloud','archive'].includes(sc))sc='primary';

            var adminBtns='';
            if(d.is_admin){
                var safeName=f.name.replace(/\\\\/g,'\\\\\\\\').replace(/'/g,"\\\\'");
                if(f.is_group) {
                    adminBtns='<div class="poster-admin">'+
                        '<button class="btn-edit" style="font-size:10px" onclick="event.stopPropagation();navigator.clipboard.writeText(\\\''+f.group_id+'\\\');showToast(\\\'📋 Group ID Copied!\\\')">📋 Copy Group ID</button>'+
                    '</div>';
                } else {
                    // ✅ FIXED: मल्टिपल एस्केपिंग बैकटैक्स पैच
                    adminBtns='<div class="poster-admin">'+
                        '<button class="btn-edit" onclick="event.stopPropagation();editFile(\\\''+f.file_id+'\\\',\\\''+f.raw_collection+'\\\',\\\''+safeName+'\\\',\\\''+(f.group_id||'')+'\\\')">&#9999; Edit</button>'+
                        '<button class="btn-del" onclick="event.stopPropagation();deleteFile(\\\''+f.file_id+'\\\',\\\''+f.raw_collection+'\\\')">&#128465; Delete</button>'+
                    '</div>';
                }
            }

            var posterHtml='';
            if(pMode!=='none'){
                posterHtml='<div class="poster-box" id="poster-box-'+f.file_id+'" onclick="toggleAdminBtns(this.closest(\\'.file-card\\'),event)">'+
                    '<img src="'+f.tg_thumb+'" id="img-poster-'+f.file_id+'" class="fc-poster" onload="this.classList.add(\\'loaded\\')" onerror="handleThumbError(\\''+f.file_id+'\\')" loading="lazy" decoding="async">'+
                    '<div class="poster-top">'+
                        '<span class="type-chip">'+f.type.toUpperCase()+'</span>'+
                        '<span class="size-chip">'+f.size+'</span>'+
                        '<span class="source-pill '+sc+'"><span class="source-dot"></span>'+sc.toUpperCase()+'</span>'+
                    '</div>'+
                    adminBtns+
                '</div>';
            }

            var textInfo='';
            if(pMode==='none'){
                textInfo='<div class="fc-text-info" onclick="toggleAdminBtns(this.closest(\\'.file-card\\'),event)">'+
                    '<span class="tc-type">'+f.type.toUpperCase()+'</span>'+
                    '<span class="tc-size">'+f.size+'</span>'+
                    '<span class="source-pill '+sc+'" style="margin-left:auto"><span class="source-dot"></span>'+sc.toUpperCase()+'</span>'+
                '</div>';
                if(d.is_admin){
                    var safeName2=f.name.replace(/\\\\/g,'\\\\\\\\').replace(/'/g,"\\\\'");
                    if(f.is_group) {
                        textInfo+='<div class="text-admin-row">'+
                            '<button class="btn-edit" style="font-size:10px" onclick="event.stopPropagation();navigator.clipboard.writeText(\\\''+f.group_id+'\\\');showToast(\\\'📋 Group ID Copied!\\\')">📋 Copy Group ID</button>'+
                        '</div>';
                    } else {
                        textInfo+='<div class="text-admin-row">'+
                            '<button class="btn-edit" onclick="event.stopPropagation();editFile(\\\''+f.file_id+'\\\',\\\''+f.raw_collection+'\\\',\\\''+safeName2+'\\\',\\\''+(f.group_id||'')+'\\\')">&#9999; Edit</button>'+
                            '<button class="btn-del" onclick="event.stopPropagation();deleteFile(\\\''+f.file_id+'\\\',\\\''+f.raw_collection+'\\\')">&#128465; Delete</button>'+
                        '</div>';
                    }
                }
            }

            var qualityChipsHtml = '';
            var titleOnclickHtml = 'window.open(\\\''+f.watch+'\\\',\\\'_blank\\\')';
            
            if(f.is_group && f.files) {
                titleOnclickHtml = "toggleAdminBtns(this.closest('.file-card'), event)";
                qualityChipsHtml = '<div class="group-quality-container">';
                f.files.forEach(function(subFile) {
                    var qLabel = 'Link';
                    var nLower = subFile.name.toLowerCase();
                    if(nLower.includes('1080p')) qLabel = '1080p';
                    else if(nLower.includes('720p')) qLabel = '720p';
                    else if(nLower.includes('480p')) qLabel = '480p';
                    else if(nLower.includes('4k') || nLower.includes('uhd')) qLabel = '4K UHD';
                    else qLabel = subFile.size;
                    
                    qualityChipsHtml += '<button class="q-chip-btn" onclick="event.stopPropagation();window.open(\\\''+subFile.watch+'\\\,\\\'_blank\\\')">' + qLabel + ' ('+subFile.size+')</button>';
                });
                qualityChipsHtml += '</div>';
            }

            h+='<div class="file-card">'+
                posterHtml+
                textInfo+
                '<div class="fc-body">'+
                    '<div class="fc-name" id="name-title-'+f.file_id+'" onclick="'+titleOnclickHtml+'">'+f.name+'</div>'+
                    qualityChipsHtml+  
                '</div>'+
            '</div>';
        });
        resDiv.innerHTML=h;
        nextOff=d.next_offset;
        document.getElementById('pageBox').style.display='flex';
        document.getElementById('pBtn').disabled=(o===0);
        document.getElementById('nBtn').disabled=!nextOff;
        document.getElementById('pgInfo').textContent='Page '+curPage;

        if(nextOff) {
            fetch('/api/search?q='+encodeURIComponent(q)+'&offset='+nextOff+'&col='+curCol+'&mode='+pMode+'&view_mode='+curViewMode);
        }
    }catch(e){showToast('Network error','error');}
}

function next(){if(nextOff){curPage++;doSearch(nextOff);scrollTo(0,0);}}
function prev(){if(curPage>1){curPage--;doSearch(Math.max(0,curOff-LIMIT_VAL));scrollTo(0,0);}}
var _tt;
function showToast(m,t){t=t||'success';var x=document.getElementById('toast');x.textContent=m;x.className='toast '+t+' show';clearTimeout(_tt);_tt=setTimeout(function(){x.classList.remove('show');},3000);}

document.addEventListener('DOMContentLoaded',function(){
    var q=document.getElementById('q');if(q)q.addEventListener('keydown',function(e){if(e.key==='Enter')doSearch(0);});
    if(pMode==='none'){
        var mItems=document.querySelectorAll('#cddModeMenu .cdd-item');
        mItems.forEach(function(i){i.classList.remove('selected');if(i.dataset.val===pMode)i.classList.add('selected');});
        document.getElementById('cddModeLabel').textContent='\u26a1 Text Only (Fastest)';
    }
});

async function deleteFile(fid,col){
    if(!confirm('Are you sure you want to delete this file?'))return;
    try{
        var r=await fetch('/api/delete',{method:'POST',body:JSON.stringify({file_id:fid,collection:col}),headers:{'Content-Type':'application/json'}});
        var res=await r.json();
        if(res.success){showToast('\\u2705 File deleted successfully!');doSearch(curOff);}
        else{showToast(res.error||'Delete failed!','error');}
    }catch(e){showToast('Delete failed','error');}
}

function editFile(fid, col, currentName, groupId){
    activeFid = fid; 
    activeCol = col;
    if(cropperInstance){cropperInstance.destroy();cropperInstance=null;}
    document.getElementById('emName').value=currentName;
    document.getElementById('emFile').value='';
    document.getElementById('cropContainer').style.display='none';

    var emNameInput = document.getElementById('emName');
    if(!document.getElementById('emAddCaption')) {
        var extraHtml = '<div style="margin-top:14px; text-align:left;">' +
            '<label style="font-size:12px;color:var(--accent);font-weight:700;">➕ Add Search Tags to Caption (Optional)</label>' +
            '<input type="text" id="emAddCaption" placeholder="e.g. Ajay Devgan, 1080p, Comedy..." style="width:100%;padding:10px;margin-top:6px;border-radius:8px;background:var(--bg3);border:1.5px solid var(--border);color:var(--text);font-family:inherit;box-sizing:border-box;">' +
            '</div>' +
            '<div style="margin-top:14px; text-align:left;">' +
            '<label style="font-size:12px;color:var(--accent);font-weight:700;">📦 Custom Group ID (Leave blank for auto-group)</label>' +
            '<input type="text" id="emGroupId" placeholder="e.g. pushpa-2-2024" style="width:100%;padding:10px;margin-top:6px;border-radius:8px;background:var(--bg3);border:1.5px solid var(--border);color:var(--text);font-family:inherit;box-sizing:border-box;">' +
            '</div>' +
            '<div style="margin-top:14px; margin-bottom:12px; text-align:left;">' +
            '<label style="font-size:12px;color:var(--accent);font-weight:700;">📂 Move File to Collection</label>' +
            '<select id="emMoveCol" style="width:100%;padding:10px;margin-top:6px;border-radius:8px;background:var(--bg3);border:1.5px solid var(--border);color:var(--text);font-family:inherit;font-weight:600;box-sizing:border-box;">' +
            '<option value="primary">🟢 Primary</option>' +
            '<option value="cloud">🔵 Cloud</option>' +
            '<option value="archive">🟠 Archive</option>' +
            '</select>' +
            '</div>';
        emNameInput.insertAdjacentHTML('afterend', extraHtml);
    }

    if(document.getElementById('emMoveCol')) {
        document.getElementById('emMoveCol').value = col;
        document.getElementById('emAddCaption').value = ''; 
        document.getElementById('emGroupId').value = groupId || ''; 
    }

    var prevBox=document.getElementById('emPreviewBox');
    prevBox.style.display='flex';
    prevBox.innerHTML='<img src="/api/thumb?file_id='+fid+'&col='+activeCol+'" class="t-prev-img" onerror="this.src=\\'https://placehold.co/600x338/181818/FFF?text=No+Thumbnail\\';">';
    document.getElementById('editCombinedModal').classList.add('open');
}

function closeCombinedModal(){
    document.getElementById('editCombinedModal').classList.remove('open');
    if(cropperInstance){cropperInstance.destroy();cropperInstance=null;}
}

function handleLocalPreview(input){
    if(input.files&&input.files[0]){
        var reader=new FileReader();
        reader.onload=function(e){
            if(cropperInstance){cropperInstance.destroy();}
            document.getElementById('emPreviewBox').style.display='none';
            var cropWrap=document.getElementById('cropContainer');
            cropWrap.style.display='block';
            cropWrap.innerHTML='<img id="cropImage" src="'+e.target.result+'" style="max-width:100%;">';
            var img=document.getElementById('cropImage');
            cropperInstance=new Cropper(img,{
                aspectRatio:16/9,viewMode:1,dragMode:'move',background:false,
                autoCropArea:1,restore:false,guides:false,center:true,highlight:false,
                cropBoxMovable:false,cropBoxResizable:false,toggleDragModeOnDblclick:false,
                zoomable:true,movable:true
            });
        };
        reader.readAsDataURL(input.files[0]);
    }
}

async function saveAllChanges(){
    var newName=document.getElementById('emName').value.trim();
    var addCaption=document.getElementById('emAddCaption') ? document.getElementById('emAddCaption').value.trim() : '';
    var moveCol=document.getElementById('emMoveCol') ? document.getElementById('emMoveCol').value : activeCol;
    var groupId=document.getElementById('emGroupId') ? document.getElementById('emGroupId').value.trim() : '';

    if(!newName){showToast('File name cannot be empty!','error');return;}
    var btn=document.getElementById('emSaveBtn');
    btn.disabled=true;btn.innerText='Processing pipeline...';
    try{
        if(cropperInstance){
            showToast('\\u2702\\ufe0f Cropping & Uploading to Telegram...');
            var canvas=cropperInstance.getCroppedCanvas({width:1280,height:720,imageSmoothingEnabled:true,imageSmoothingQuality:'high'});
            var blob=await new Promise(function(resolve){canvas.toBlob(resolve,'image/jpeg',0.9);});
            if(blob){
                var formData=new FormData();
                formData.append('file_id',activeFid);
                formData.append('collection',activeCol);
                formData.append('image',blob,'cropped_poster.jpg');
                var upRes=await fetch('/api/upload_thumb',{method:'POST',body:formData});
                var upData=await upRes.json();
                if(!upData.success){showToast(upData.error||'Telegram image sync failed!','error');btn.disabled=false;btn.innerText='Save Changes';return;}
            }
        }
        showToast('\\ud83d\\udcbe Updating DB & Collection...');
        
        var payload = {
            file_id: activeFid,
            collection: activeCol,
            new_name: newName,
            add_caption: addCaption,
            target_collection: moveCol,
            group_id: groupId
        };

        var r=await fetch('/api/edit_name',{method:'POST',body:JSON.stringify(payload),headers:{'Content-Type':'application/json'}});
        var res=await r.json();
        
        if(res.success||cropperInstance){
            showToast('\\u2728 File updated successfully!');
            closeCombinedModal();
            doSearch(curOff);
        }else{showToast(res.error||'Metadata save failed!','error');}
    }catch(e){showToast('Network synchronization error','error');}
    finally{btn.disabled=false;btn.innerText='Save Changes';}
}
""".replace("__LIMIT_PLACEHOLDER__", str(MAX_WEB_RESULTS))

SEARCH_ZONE = (
    '<div class="search-zone">'
        '<div class="search-row1">'
            '<div class="search-wrap">'
                '<input class="search-input" id="q" placeholder="Titles, people, genres\u2026">'
            '</div>'
            '<button class="search-btn" id="searchBtn" onclick="doSearch(0);triggerRipple(this)">Search</button>'
        '</div>'
        '<div class="search-row2">'
            '<div class="cdd-wrap" id="cddColWrap">'
                '<div class="cdd-btn" id="cddColBtn" onclick="toggleCdd(\'col\')">'
                    '<span id="cddColLabel">\U0001f4c2 All Collections</span>'
                '</div>'
                '<span class="cdd-arrow">&#9660;</span>'
                '<div class="cdd-menu" id="cddColMenu" style="display:none">'
                    '<div class="cdd-item selected" data-val="all" onclick="pickCol(\'all\',\'\U0001f4c2 All Collections\',this)">\U0001f4c2 All Collections<span class="cdd-radio"><span class="cdd-radio-dot"></span></span></div>'
                    '<div class="cdd-item" data-val="primary" onclick="pickCol(\'primary\',\'\U0001f7e2 Primary\',this)">\U0001f7e2 Primary<span class="cdd-radio"><span class="cdd-radio-dot"></span></span></div>'
                    '<div class="cdd-item" data-val="cloud" onclick="pickCol(\'cloud\',\'\U0001f535 Cloud\',this)">\U0001f535 Cloud<span class="cdd-radio"><span class="cdd-radio-dot"></span></span></div>'
                    '<div class="cdd-item" data-val="archive" onclick="pickCol(\'archive\',\'\U0001f7e0 Archive\',this)">\U0001f7e0 Archive<span class="cdd-radio"><span class="cdd-radio-dot"></span></span></div>'
                '</div>'
            '</div>'
            '<div class="cdd-wrap" id="cddModeWrap">'
                '<div class="cdd-btn" id="cddModeBtn" onclick="toggleCdd(\'mode\')">'
                    '<span id="cddModeLabel">\U0001f4f8 Original TG Thumb</span>'
                '</div>'
                '<span class="cdd-arrow">&#9660;</span>'
                '<div class="cdd-menu" id="cddModeMenu" style="display:none">'
                    '<div class="cdd-item selected" data-val="tg" onclick="pickMode(\'tg\',\'\U0001f4f8 Original TG Thumb\',this)">\U0001f4f8 Original TG Thumb<span class="cdd-radio"><span class="cdd-radio-dot"></span></span></div>'
                    '<div class="cdd-item" data-val="none" onclick="pickMode(\'none\',\'\u26a1 Text Only (Fastest)\',this)">\u26a1 Text Only (Fastest)<span class="cdd-radio"><span class="cdd-radio-dot"></span></span></div>'
                '</div>'
            '</div>'
            '<div class="cdd-wrap" id="cddViewWrap" style="display:none">'
                '<div class="cdd-btn" id="cddViewBtn" onclick="toggleCdd(\'view\')">'
                    '<span id="cddViewLabel">👥 Group View</span>'
                '</div>'
                '<span class="cdd-arrow">&#9660;</span>'
                '<div class="cdd-menu" id="cddViewMenu" style="display:none">'
                    '<div class="cdd-item selected" data-val="group" onclick="pickViewMode(\'group\',\'👥 Group View\',this)">👥 Group View<span class="cdd-radio"><span class="cdd-radio-dot"></span></span></div>'
                    '<div class="cdd-item" data-val="single" onclick="pickViewMode(\'single\',\'📄 Single File View\',this)">📄 Single File View<span class="cdd-radio"><span class="cdd-radio-dot"></span></span></div>'
                '</div>'
            '</div>'
        '</div>'
    '</div>'
    '<div class="main" style="padding-top:4px;">'
        '<div class="results-info" id="resInfo" style="padding:0 12px 8px;">'
            '<span class="results-count" id="resCount"></span>'
        '</div>'
        '<div style="padding:0 2px">'
            '<div id="results" class="res-grid">'
                '<div class="empty"><div class="empty-icon">&#8981;</div>'
                '<p>Find your favorite movies and TV shows.</p></div>'
            '</div>'
            '<div class="pagination" id="pageBox" style="display:none;">'
                '<button class="pg-btn" id="pBtn" onclick="prev()" disabled>Previous</button>'
                '<span class="pg-info" id="pgInfo">Page 1</span>'
                '<button class="pg-btn" id="nBtn" onclick="next()">Next</button>'
            '</div>'
        '</div>'
    '</div>'
    '<div class="toast" id="toast"></div>'
)

DASHBOARD_BODY = CARD_CSS + SEARCH_ZONE + f"<script>{JS_ENGINE}</script>"

@dashboard_routes.get('/dashboard')
async def dash(req):
    role, tg_id = await get_auth(req)
    if not role:
        return web.HTTPFound('/login')
    if role == 'user':
        mp = await user_db.get_plan(tg_id)
        if not mp.get("premium"):
            return web.HTTPFound('/premium_expired')

    return build_page("Home - Fast Finder", DASHBOARD_BODY, "", "dash", role)

@dashboard_routes.get('/logout')
async def logout(req):
    s_user = req.cookies.get('user_session')
    if s_user and hasattr(temp, 'USER_SESSIONS') and s_user in temp.USER_SESSIONS:
        del temp.USER_SESSIONS[s_user]
    res = web.HTTPFound('/login')
    res.del_cookie('user_session')
    return res

@dashboard_routes.get('/premium_expired')
async def premium_expired(req):
    role, tg_id = await get_auth(req)
    if not role:
        return web.HTTPFound('/login')
    content = (
        '<div style="text-align:center;">'
        '<div style="font-size:50px;margin-bottom:15px;">&#9203;</div>'
        '<p style="color:var(--muted);margin-bottom:30px;">Your access to Fast Finder Web has expired. '
        'Please renew your plan via our Telegram Bot.</p>'
        '<div class="scard red" style="text-align:left;margin-bottom:25px;padding:15px;">'
        '<div class="scard-label">How to Renew?</div>'
        '<div class="scard-sub" style="color:var(--text)">1. Go to Telegram Bot</div>'
        '<div class="scard-sub" style="color:var(--text)">2. Use command <b>/plan</b></div>'
        '<div class="scard-sub" style="color:var(--text)">3. Pay & Activate instantly</div>'
        '</div>'
        f'<a href="https://t.me/{temp.U_NAME}" class="submit-btn" style="text-decoration:none;display:block;">Open Telegram Bot</a>'
        '<a href="/logout" style="display:block;margin-top:20px;color:var(--muted);text-decoration:none;">Sign Out</a>'
        '</div>'
    )
    return build_page("Premium Expired", form_wrapper("Premium Expired", content), "login-bg")

@dashboard_routes.get('/health')
async def koyeb_health_check(req):
    return web.json_response({"status": "alive", "platform": "koyeb"})
