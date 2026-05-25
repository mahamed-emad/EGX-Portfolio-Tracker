/**
 * app.js — نظام إدارة محفظة البورصة المصرية
 * كل وظيفة منفصلة ومنظمة
 */

// ══════════════════════════════════════════════
// STATE
// ══════════════════════════════════════════════
let currentLogFilter = 'all';
let acTimer = null;
let allStocksCache = [];

// ══════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', async () => {
    startClock();
    document.addEventListener('click', e => {
        if (!e.target.closest('.form-group')) closeAC();
    });
    const res = await apiFetch('/api/session');
    if (res.ok && res.data.username) {
        await enterApp(res.data.username);
    } else {
        showPicker();
    }
});

// ══════════════════════════════════════════════
// CLOCK
// ══════════════════════════════════════════════
function startClock() {
    const el = document.getElementById('clock');
    const tick = () => {
        const n = new Date(), p = x => String(x).padStart(2,'0');
        if (el) el.textContent = `${p(n.getHours())}:${p(n.getMinutes())}:${p(n.getSeconds())}`;
    };
    tick(); setInterval(tick, 1000);
}

// ══════════════════════════════════════════════
// API
// ══════════════════════════════════════════════
async function apiFetch(url, opts = {}) {
    try {
        const r = await fetch(url, { headers: {'Content-Type':'application/json'}, ...opts });
        return await r.json();
    } catch(e) { return {ok:false, error:'خطأ في الاتصال'}; }
}
const apiPost = (url, body) => apiFetch(url, {method:'POST', body:JSON.stringify(body)});
const apiDel  = (url)       => apiFetch(url, {method:'DELETE'});

// ══════════════════════════════════════════════
// LOADING
// ══════════════════════════════════════════════
function showLoading(msg='') {
    const el = document.getElementById('loading');
    const lm = document.getElementById('loading-msg');
    if (el) el.classList.add('show');
    if (lm && msg) lm.textContent = msg;
}
function hideLoading() {
    const el = document.getElementById('loading');
    if (el) el.classList.remove('show');
}

// ══════════════════════════════════════════════
// TOAST
// ══════════════════════════════════════════════
function showToast(msg, type = 'info') {
    const c = document.getElementById('toast');
    if (!c) return;
    const t = document.createElement('div');
    t.className = `toast ${type}`;
    t.innerHTML = `<span>${{success:'✅',error:'❌',info:'ℹ️'}[type]||'ℹ️'}</span> ${msg}`;
    c.appendChild(t);
    setTimeout(() => {
        t.style.opacity='0'; t.style.transition='opacity .4s';
        setTimeout(()=>t.remove(),400);
    }, 4500);
}

// ══════════════════════════════════════════════
// FORMATTERS
// ══════════════════════════════════════════════
const fmt    = (n,d=2)  => (n===null||n===undefined||isNaN(n)) ? '--'
    : Number(n).toLocaleString('en-EG',{minimumFractionDigits:d,maximumFractionDigits:d});
const fmtJ   = n => fmt(n)==='--' ? '--' : fmt(n)+' ج';
const fmtPct = n => {
    if (n===null||n===undefined||isNaN(n)) return '--';
    return (n>=0?'+':'')+fmt(n)+'%';
};
const setText = (id,v) => { const e=document.getElementById(id); if(e) e.textContent=v; };

// ══════════════════════════════════════════════
// SCREEN SWITCHING
// ══════════════════════════════════════════════
function showPicker() {
    document.getElementById('screen-picker').style.display = 'flex';
    document.getElementById('screen-app').style.display   = 'none';
    loadPickerUsers();
}

async function enterApp(username) {
    document.getElementById('screen-picker').style.display = 'none';
    document.getElementById('screen-app').style.display    = 'block';

    await apiPost('/api/session', {username});

    // اسم المستخدم في الهيدر
    const users = await apiFetch('/api/users');
    const user  = (users.data||[]).find(u => u.username === username);
    const name  = user ? user.display_name : username;
    setText('user-label', name);
    const av = document.getElementById('user-avatar');
    if (av) av.textContent = name.charAt(0);

    // جلب أسعار أسهم المحفظة فور الدخول
    await refreshPortfolio();

    // تحديث تلقائي كل 3 دقائق
    setInterval(refreshPortfolio, 180000);
}

async function logout() {
    await apiDel('/api/session');
    showPicker();
}

// ══════════════════════════════════════════════
// PICKER
// ══════════════════════════════════════════════
async function loadPickerUsers() {
    const res  = await apiFetch('/api/users');
    const wrap = document.getElementById('picker-users');
    if (!wrap) return;
    const users = res.data || [];
    if (users.length === 0) {
        wrap.innerHTML = '<div class="picker-empty">لا توجد محافظ — أنشئ محفظتك الأولى ⬇</div>';
        return;
    }
    wrap.innerHTML = users.map(u => `
        <div class="picker-user-card" onclick="enterApp('${u.username}')">
            <div class="picker-avatar">${u.display_name.charAt(0)}</div>
            <div class="picker-uname">${u.display_name}</div>
            <div class="picker-uid">${u.username}</div>
        </div>
    `).join('');
}

async function createUser() {
    const dname = document.getElementById('nu-dname').value.trim();
    const uname = document.getElementById('nu-username').value.trim();
    if (!dname || !uname) return showToast('أدخل الاسم المعروض واسم المستخدم','error');
    const res = await apiPost('/api/users', {display_name: dname, username: uname});
    if (res.ok) {
        showToast(res.message,'success');
        document.getElementById('nu-dname').value = '';
        document.getElementById('nu-username').value = '';
        await enterApp(res.data.username);
    } else {
        showToast(res.error,'error');
    }
}

// ══════════════════════════════════════════════
// TABS
// ══════════════════════════════════════════════
function switchTab(name) {
    document.querySelectorAll('.tab-content').forEach(t=>t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    document.getElementById(`tab-${name}`).classList.add('active');
    document.querySelector(`[data-tab="${name}"]`).classList.add('active');
    if (name==='log')    loadLog();
    if (name==='stocks') loadStocksDB();
}

// ══════════════════════════════════════════════
// REFRESH — زرار واحد يجيب الأسعار ويحدث كل حاجة
// ══════════════════════════════════════════════
async function refreshPortfolio() {
    const icon = document.getElementById('refresh-icon');
    const btn  = document.querySelector('.refresh-btn');
    if (icon) icon.style.animation = 'spin .8s linear infinite';
    if (btn)  btn.disabled = true;

    showLoading('جاري جلب أسعار الأسهم...');

    try {
        // جلب الأسعار من الإنترنت + تحديث المحفظة في خطوة واحدة
        const res = await apiFetch('/api/market/refresh', {method:'POST'});

        if (res.ok && res.data) {
            // تحديث الكروت بالبيانات الجديدة مباشرة
            updateSummaryCards(res.data.summary);
        }

        // تحديث جدول الأسهم
        await loadHoldings();

    } catch(e) {
        showToast('خطأ في تحديث الأسعار', 'error');
    } finally {
        hideLoading();
        if (icon) icon.style.animation = '';
        if (btn)  btn.disabled = false;
    }
}

// ══════════════════════════════════════════════
// SUMMARY CARDS
// ══════════════════════════════════════════════
function updateSummaryCards(d) {
    if (!d) return;
    setText('val-deposited', fmtJ(d.total_deposited));
    setText('val-withdrawn',  fmtJ(d.total_withdrawn));
    setText('val-cash',       fmtJ(d.cash_balance));
    setText('val-net',        fmtJ(d.net_invested));
    setText('val-total',      fmtJ(d.total_portfolio_value));
    setText('val-stocks',     fmtJ(d.stocks_market_value));
    const isP = d.total_profit_amount >= 0;
    const card = document.getElementById('card-profit');
    if (card) { card.classList.remove('profit','loss'); card.classList.add(isP?'profit':'loss'); }
    setText('val-profit-amt', (isP?'+':'')+fmtJ(d.total_profit_amount));
    setText('val-profit-pct', fmtPct(d.total_profit_pct));
}

async function loadSummary() {
    const res = await apiFetch('/api/summary');
    if (res.ok) updateSummaryCards(res.data);
}

// ══════════════════════════════════════════════
// HOLDINGS TABLE
// ══════════════════════════════════════════════
async function loadHoldings() {
    const res   = await apiFetch('/api/holdings');
    const tbody = document.getElementById('holdings-body');
    if (!tbody) return;

    if (!res.ok || !res.data || res.data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="8" class="empty-row">📭 لا توجد أسهم في المحفظة</td></tr>`;
        return;
    }

    tbody.innerHTML = res.data.map(h => {
        const cls    = h.profit_loss_pct===null ? '' : h.profit_loss_pct>=0 ? 'cell-profit' : 'cell-loss';
        const pText  = h.profit_loss_pct===null
            ? `<span style="color:var(--text-dim);font-size:11px">--</span>`
            : `<strong class="${cls}">${fmtPct(h.profit_loss_pct)}</strong>`;
        const aText  = h.profit_loss_amount===null ? '--'
            : `<span class="${cls}">${h.profit_loss_amount>=0?'+':''}${fmtJ(h.profit_loss_amount)}</span>`;

        // السعر الحالي + التغيير اليومي
        let cPrice = `<span style="color:var(--text-dim)">--</span>`;
        if (h.current_price) {
            const cp  = h.change_percent;
            const cs  = cp>0 ? 'color:var(--green)' : cp<0 ? 'color:var(--red)' : 'color:var(--text-dim)';
            const csn = cp>=0 ? '+' : '';
            const chg = (cp!==null&&cp!==undefined)
                ? ` <small style="${cs};font-size:10px">(${csn}${fmt(cp)}%)</small>` : '';
            cPrice = `<span style="color:var(--accent-teal)">${fmtJ(h.current_price)}</span>${chg}`;
        }

        return `<tr>
            <td><span class="code-badge">${h.stock_code}</span></td>
            <td>${h.stock_name}</td>
            <td class="mono">${fmt(h.quantity,0)}</td>
            <td class="mono">${fmtJ(h.total_cost)}</td>
            <td class="mono">${fmtJ(h.avg_price)}</td>
            <td class="mono">${cPrice}</td>
            <td class="mono">${aText}</td>
            <td>${pText}</td>
        </tr>`;
    }).join('');
}

// ══════════════════════════════════════════════
// LOG
// ══════════════════════════════════════════════
async function loadLog(filter) {
    if (filter !== undefined) currentLogFilter = filter;
    const url   = currentLogFilter==='all' ? '/api/transactions' : `/api/transactions?type=${currentLogFilter}`;
    const res   = await apiFetch(url);
    const tbody = document.getElementById('log-body');
    if (!tbody) return;
    if (!res.ok || !res.data || res.data.length===0) {
        tbody.innerHTML = `<tr><td colspan="9" class="empty-row">📋 لا توجد عمليات</td></tr>`;
        return;
    }
    const TL = {buy:'شراء',sell:'بيع',deposit:'إيداع',withdraw:'سحب'};
    tbody.innerHTML = res.data.map((tx,i)=>`<tr>
        <td class="mono" style="color:var(--text-dim)">${res.data.length-i}</td>
        <td><span class="badge badge-${tx.type}">${TL[tx.type]||tx.type}</span></td>
        <td class="mono" style="font-size:12px;color:var(--text-muted)">${tx.created_at?.substring(0,16)||'--'}</td>
        <td>${tx.stock_code?`<span class="code-badge">${tx.stock_code}</span>`:'--'}</td>
        <td>${tx.stock_name||'--'}</td>
        <td class="mono">${tx.quantity?fmt(tx.quantity,0):'--'}</td>
        <td class="mono">${tx.price_per_share?fmtJ(tx.price_per_share):'--'}</td>
        <td class="mono" style="font-weight:700">${fmtJ(tx.amount)}</td>
        <td style="color:var(--text-muted);font-size:12px">${tx.notes||'--'}</td>
    </tr>`).join('');
}

function filterLog(type,btn) {
    document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    loadLog(type);
}

// ══════════════════════════════════════════════
// AUTOCOMPLETE
// ══════════════════════════════════════════════
function liveSearch(input, nameId, acId) {
    const q    = input.value.trim();
    const list = document.getElementById(acId);
    const nameEl = document.getElementById(nameId);
    if (!list) return;
    if (q.length < 1) { list.classList.remove('show'); if(nameEl) nameEl.value=''; return; }
    clearTimeout(acTimer);
    acTimer = setTimeout(async () => {
        const res = await apiFetch(`/api/stocks/search?q=${encodeURIComponent(q)}`);
        if (!res.ok || !res.data?.length) { list.classList.remove('show'); return; }
        const exact = res.data.find(s=>s.code===q.toUpperCase());
        if (exact && nameEl) nameEl.value = exact.name;
        list.innerHTML = res.data.map(s=>`
            <div class="autocomplete-item"
                 onclick="pickStock('${input.id}','${nameId}','${acId}','${s.code}','${s.name.replace(/'/g,"\\'")}')">
                <span class="ac-code">${s.code}</span>
                <span class="ac-name">${s.name}</span>
            </div>`).join('');
        list.classList.add('show');
    }, 180);
}

function pickStock(codeId, nameId, acId, code, name) {
    const codeEl = document.getElementById(codeId);
    const nameEl = document.getElementById(nameId);
    if (codeEl) codeEl.value = code;
    if (nameEl) nameEl.value = name;
    document.getElementById(acId)?.classList.remove('show');
    buyPreview();
}
function closeAC() { document.querySelectorAll('.autocomplete-list').forEach(l=>l.classList.remove('show')); }

// ══════════════════════════════════════════════
// BUY PREVIEW
// ══════════════════════════════════════════════
function buyPreview() {
    const qty  = parseFloat(document.getElementById('buy-qty')?.value);
    const amt  = parseFloat(document.getElementById('buy-amt')?.value);
    const el   = document.getElementById('buy-preview');
    if (!el) return;
    if (qty>0 && amt>0) {
        el.innerHTML = `💡 سعر السهم الواحد: <strong style="color:var(--accent-blue)">${fmt(amt/qty)} ج</strong>
            &nbsp;|&nbsp; إجمالي: <strong style="color:var(--accent-gold)">${fmtJ(amt)}</strong>`;
        el.classList.add('show');
    } else { el.classList.remove('show'); }
}

// ══════════════════════════════════════════════
// CLEAR FORMS
// ══════════════════════════════════════════════
function clearForm(...ids) { ids.forEach(id=>{ const e=document.getElementById(id); if(e) e.value=''; }); }

// ══════════════════════════════════════════════
// OPERATIONS
// ══════════════════════════════════════════════
async function doBuy() {
    const code  = document.getElementById('buy-code')?.value.trim().toUpperCase();
    const qty   = parseInt(document.getElementById('buy-qty')?.value||'0');
    const amt   = parseFloat(document.getElementById('buy-amt')?.value||'0');
    const notes = document.getElementById('buy-notes')?.value.trim();
    if (!code)        return showToast('أدخل كود السهم','error');
    if (!qty||qty<=0) return showToast('أدخل عدد الأسهم','error');
    if (!amt||amt<=0) return showToast('أدخل المبلغ المدفوع','error');
    showLoading('جاري تنفيذ الشراء...');
    const res = await apiPost('/api/buy',{code,quantity:qty,amount:amt,notes});
    hideLoading();
    if (res.ok) {
        showToast(res.message,'success');
        clearForm('buy-code','buy-name','buy-qty','buy-amt','buy-notes');
        document.getElementById('buy-preview')?.classList.remove('show');
        await refreshPortfolio();
        loadLog();
    } else showToast(res.error,'error');
}

async function doSell() {
    const code  = document.getElementById('sell-code')?.value.trim().toUpperCase();
    const qty   = parseInt(document.getElementById('sell-qty')?.value||'0');
    const amt   = parseFloat(document.getElementById('sell-amt')?.value||'0');
    const notes = document.getElementById('sell-notes')?.value.trim();
    if (!code)        return showToast('أدخل كود السهم','error');
    if (!qty||qty<=0) return showToast('أدخل عدد الأسهم','error');
    if (!amt||amt<=0) return showToast('أدخل مبلغ البيع','error');
    showLoading('جاري تنفيذ البيع...');
    const res = await apiPost('/api/sell',{code,quantity:qty,amount:amt,notes});
    hideLoading();
    if (res.ok) {
        showToast(res.message,'success');
        clearForm('sell-code','sell-name','sell-qty','sell-amt','sell-notes');
        await refreshPortfolio();
        loadLog();
    } else showToast(res.error,'error');
}

async function doDeposit() {
    const amt   = parseFloat(document.getElementById('dep-amt')?.value||'0');
    const notes = document.getElementById('dep-notes')?.value.trim();
    if (!amt||amt<=0) return showToast('أدخل مبلغ الإيداع','error');
    showLoading();
    const res = await apiPost('/api/deposit',{amount:amt,notes});
    hideLoading();
    if (res.ok) {
        showToast(res.message,'success');
        clearForm('dep-amt','dep-notes');
        await loadSummary();
        loadLog();
    } else showToast(res.error,'error');
}

async function doWithdraw() {
    const amt   = parseFloat(document.getElementById('wit-amt')?.value||'0');
    const notes = document.getElementById('wit-notes')?.value.trim();
    if (!amt||amt<=0) return showToast('أدخل مبلغ السحب','error');
    showLoading();
    const res = await apiPost('/api/withdraw',{amount:amt,notes});
    hideLoading();
    if (res.ok) {
        showToast(res.message,'success');
        clearForm('wit-amt','wit-notes');
        await loadSummary();
        loadLog();
    } else showToast(res.error,'error');
}

// ══════════════════════════════════════════════
// STOCKS DATABASE TAB
// ══════════════════════════════════════════════
async function loadStocksDB() {
    const tbody   = document.getElementById('stocks-body');
    const countEl = document.getElementById('stocks-count');
    if (!tbody) return;
    const res = await apiFetch('/api/stocks/all');
    if (!res.ok) { tbody.innerHTML=`<tr><td colspan="3" class="empty-row">خطأ</td></tr>`; return; }
    allStocksCache = res.data || [];
    renderStocksTable(allStocksCache);
    if (countEl) countEl.textContent = `${allStocksCache.length} سهم`;
}

function renderStocksTable(stocks) {
    const tbody = document.getElementById('stocks-body');
    if (!stocks.length) { tbody.innerHTML=`<tr><td colspan="3" class="empty-row">لا توجد أسهم</td></tr>`; return; }
    tbody.innerHTML = stocks.map(s=>`<tr>
        <td><span class="code-badge">${s.code}</span></td>
        <td>${s.name}</td>
        <td><span class="sector-badge">${s.sector||'--'}</span></td>
    </tr>`).join('');
}

function searchStocksDB() {
    const q = document.getElementById('stocks-search')?.value.trim().toLowerCase();
    if (!q) { renderStocksTable(allStocksCache); return; }
    renderStocksTable(allStocksCache.filter(s=>
        s.code.toLowerCase().includes(q) || s.name.includes(q) || (s.sector||'').includes(q)
    ));
}

async function addSingleStock() {
    const code   = document.getElementById('as-code')?.value.trim().toUpperCase();
    const name   = document.getElementById('as-name')?.value.trim();
    const sector = document.getElementById('as-sector')?.value.trim() || 'أخرى';
    if (!code || !name) return showToast('الكود والاسم مطلوبان','error');
    const res = await apiPost('/api/stocks/add',{code,name,sector});
    if (res.ok) { showToast(res.message,'success'); clearForm('as-code','as-name','as-sector'); loadStocksDB(); }
    else showToast(res.error,'error');
}

async function doBulkAdd() {
    const raw = document.getElementById('bulk-input')?.value.trim();
    if (!raw) return showToast('أدخل بيانات الأسهم','error');
    const stocks = [];
    raw.split('\n').forEach((line,i) => {
        const parts = line.trim().split(',');
        if (parts.length < 2) return;
        const [code, name, sector='أخرى'] = parts.map(p=>p.trim());
        if (code && name) stocks.push({code, name, sector});
    });
    if (!stocks.length) return showToast('لا توجد بيانات صحيحة','error');
    showLoading();
    const res = await apiPost('/api/stocks/bulk',{stocks});
    hideLoading();
    if (res.ok) {
        showToast(res.message,'success');
        document.getElementById('bulk-input').value = '';
        loadStocksDB();
    } else showToast(res.error,'error');
}
