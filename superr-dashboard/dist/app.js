'use strict';
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
const state = { data: null, role: 'batter', tableRole: 'batter', active: -1, progress: 0, pending: false };
const escapeHTML = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = (v, places = 1) => Number(v).toFixed(places);
const count = v => Number(v).toLocaleString('en-US', { maximumFractionDigits: 0 });
const rate = (p, ordinary = false) => p[(ordinary ? 'ordinary_' : 'high_') + (p.role === 'batter' ? 'strike_rate' : 'economy')];
const settings = p => Math.round(p.scenario_top10_frequency * 13);
const colours = ['#f6b6d8','#ef9fcb','#f5c1de','#e998c6','#f0b0d2','#e5a5d0','#f7bad8','#eba0cb','#f2c4e0','#dfacd0'];

function renderDeck() {
  const category = state.role;
  $('.deck').innerHTML = state.data[category].slice(0,10).map((p,i) => {
    const role=p.role;
    const name = p.player_name.split(' '), last = name.pop(), first = name.join(' ');
    const summary = role === 'batter'
      ? `${count(p.high_runs)} pressure runs. ${count(p.high_dismissals)} dismissals.<br>Evidence from ${count(p.high_matches)} pressure matches.`
      : `${count(p.high_dismissals)} pressure wickets.<br>Evidence from ${count(p.high_matches)} pressure matches.`;
    const dots = Array.from({length:13}, (_,j) => `<i class="${j < settings(p) ? 'on' : ''}"></i>`).join('');
    return `<article class="player-card" id="player-${p.player_id}" style="--card-color:${colours[i]}" aria-label="Rank ${i+1}: ${escapeHTML(p.player_name)}" ${reducedMotion.matches ? '' : 'inert aria-hidden="true"'}>
      <div class="card-body"><span class="rank-watermark" aria-hidden="true">${String(i+1).padStart(2,'0')}</span>
        <div class="card-kicker"><span class="rank-badge">${String(i+1).padStart(2,'0')}</span> ${role === 'batter' ? 'BATTER' : 'BOWLER'} / ${category==='uncapped'?'UNCAPPED WATCHLIST':'UNDER PRESSURE'}</div>
        <h3 class="card-name">${escapeHTML(first)}<br>${escapeHTML(last)}</h3><p class="card-summary">${summary}</p>
        <div class="card-stability"><span class="stability-dots" aria-hidden="true">${dots}</span><b>${settings(p)}/13</b> ${category==='uncapped'?'MAIN-LIST CHECKS':'TOP-10 CHECKS'} <a class="checks-link check-help" href="#model-checks" aria-label="Explain top-ten checks and model settings">?</a></div>
        <img class="card-photo" src="${p.photo}" alt="${escapeHTML(p.player_name)}" ${i > 2 ? 'loading="lazy"' : ''} width="500" height="600">
      </div>
      <div class="card-metrics"><div><strong>${fmt(rate(p),role === 'batter'?1:2)}</strong><span>HP ${role === 'batter' ? 'strike rate' : 'economy'}</span></div><div><strong>${fmt(rate(p,true),role === 'batter'?1:2)}</strong><span>Ordinary ${role === 'batter' ? 'SR' : 'economy'}</span></div><div><strong>${count(p.high_units)}</strong><span>HP ${role === 'batter' ? 'balls faced' : 'legal balls'}</span></div><div><strong>${fmt(p.consensus_index)}</strong><span>Consensus index</span></div></div>
      <div class="card-fit"><div class="fit-heading"><b>THE ROYALS FIT</b><span>${escapeHTML(p.status)}</span></div><p>${escapeHTML(p.fit)}</p></div>
    </article>`;
  }).join('');
  state.active = -1;
  updateCards();
}

function jumpTo(index, behavior = 'smooth') {
  index = Math.max(0,Math.min(9,index));
  if (reducedMotion.matches) { $$('.player-card')[index].scrollIntoView({behavior:'auto',block:'center'}); return; }
  const section = $('#rankings');
  const sticky = $('.ranking-sticky');
  const start = section.offsetTop - parseFloat(getComputedStyle(sticky).top);
  const range = section.offsetHeight - sticky.offsetHeight;
  window.scrollTo({ top: start + (index/9)*range, behavior });
}

function updateCards() {
  if (!state.data) return;
  const section = $('#rankings'), sticky = $('.ranking-sticky');
  const start = section.offsetTop - parseFloat(getComputedStyle(sticky).top || 0);
  const range = Math.max(1,section.offsetHeight-sticky.offsetHeight);
  const progress = Math.max(0,Math.min(9, ((window.scrollY-start)/range)*9));
  state.progress = progress;
  const active = Math.min(9,Math.floor(progress + .5));
  $$('.player-card').forEach((card,i) => {
    if (reducedMotion.matches) {card.inert=false;card.removeAttribute('aria-hidden');return;}
    const d = i-progress;
    let transform, opacity;
    if (d >= 0) {
      transform = `translate3d(0,${d*12}px,${-d*60}px) rotateZ(${d*-1.6}deg) scale(${Math.max(.5,1-d*.022)})`;
      opacity = d > 3 ? 0 : Math.max(0,1-d*.13);
    } else {
      const t = Math.min(1,-d);
      transform = `translate3d(${t*28}px,${-t*530}px,${t*120}px) rotateX(${t*10}deg) rotateZ(${t*3}deg)`;
      opacity = Math.max(0,1-t*2.1);
    }
    card.style.transform=transform;card.style.opacity=opacity;card.style.zIndex=20-i;
    card.style.pointerEvents = i === active ? 'auto' : 'none';
    card.inert = i !== active;
    card.setAttribute('aria-hidden',i === active ? 'false':'true');
  });
  if (state.active !== active) {
    state.active = active;
    $$('.rank-jumps button').forEach((b,i)=>{b.classList.toggle('current',i===active);b.setAttribute('aria-pressed',String(i===active));});
    $('#rank-count').textContent = `${String(active+1).padStart(2,'0')} — 10`;
    $('#progress').style.width = `${(active+1)*10}%`;
    $('#previous').disabled=active===0;$('#next').disabled=active===9;
    $('#rank-announcement').textContent = `${state.role==='uncapped'?'Watchlist':state.role==='batter'?'Batter':'Bowler'} rank ${active+1}: ${state.data[state.role][active].player_name}`;
  }
}

function renderTable() {
  const role = state.tableRole, isBat=role==='batter';
  if(role==='uncapped'){renderWatchlistTable();return;}
  const term=$('#player-search').value.trim().toLowerCase();
  const rows=state.data[role].filter(p=>p.player_name.toLowerCase().includes(term));
  $('#table-head').innerHTML=`<tr><th scope="col">Rank</th><th scope="col">Player</th><th scope="col">Index</th><th scope="col">HP ${isBat?'SR ↑':'econ ↓'}</th><th scope="col">Ordinary ${isBat?'SR':'econ'}</th><th scope="col">HP balls</th><th scope="col">HP ${isBat?'outs':'wickets'}</th><th scope="col">HP matches</th><th scope="col" title="Number of 13 analysis versions in which the player was selected in the top ten">Top-10 checks</th><th scope="col">Bootstrap top 10*</th></tr>`;
  $('#table-body').innerHTML=rows.length ? rows.map(p=>`<tr class="${p.final_rank<=10?'selected':''}"><td>${String(p.final_rank).padStart(2,'0')}</td><td>${escapeHTML(p.player_name)}</td><td><span class="index-bar" style="--value:${p.consensus_index}%">${fmt(p.consensus_index)}</span></td><td><b>${fmt(rate(p),isBat?1:2)}</b></td><td class="ordinary">${fmt(rate(p,true),isBat?1:2)}</td><td>${count(p.high_units)}</td><td>${count(p.high_dismissals)}</td><td>${count(p.high_matches)}</td><td>${settings(p)}/13</td><td>${fmt(p.primary_bootstrap_top10_frequency*100)}%</td></tr>`).join(''):'<tr><td colspan="10" style="text-align:center;padding:35px">No matching players in this top 20.</td></tr>';
  $('#csv-link').href=`top10_${isBat?'batters':'bowlers'}.csv`;
  $('#csv-link').textContent='Download top 10 CSV ↓';
  $('.table-key span').innerHTML='<i></i> Final top 10';
  $('#finding-text').innerHTML=isBat
    ? '<b>Why Patidar ahead of Iyer?</b> Patidar’s mean rank across the 13 settings is 3.77 versus Iyer’s 3.92. Iyer has the higher raw pressure strike rate (175.9 vs 162.0); context, dismissals, sample size and uncertainty also affect the final order.'
    : '<b>Why Kuldeep ahead of Mustafizur?</b> Kuldeep’s mean rank is 1.23 versus 1.85. Both are top ten in all 13 settings; Kuldeep’s pressure economy is 6.35 versus 6.48. Peer context and wicket value also contribute to the ranking.';
  $$('.table-tab').forEach(b=>{const active=b.dataset.role===role;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
}

function renderWatchlistTable(){
 const term=$('#player-search').value.trim().toLowerCase();
 const rows=state.data.uncapped.filter(p=>p.player_name.toLowerCase().includes(term));
 $('#table-head').innerHTML='<tr><th>Rank</th><th>Player</th><th>Role</th><th>Index</th><th>HP SR / econ</th><th>HP balls</th><th>HP matches</th><th>Evidence tier</th></tr>';
 $('#table-body').innerHTML=rows.length?rows.map(p=>`<tr class="${p.final_rank<=2?'selected':''}"><td>${p.final_rank}</td><td>${escapeHTML(p.player_name)}</td><td>${p.role}</td><td>${fmt(p.consensus_index,2)}</td><td>${fmt(rate(p),p.role==='batter'?1:2)} ${p.role==='batter'?'SR':'econ'}</td><td>${count(p.high_units)}</td><td>${count(p.high_matches)}</td><td>${escapeHTML(p.status)}</td></tr>`).join(''):'<tr><td colspan="8">No matching watchlist players.</td></tr>';
 $('#csv-link').href='uncapped_watchlist.csv';$('#csv-link').textContent='Download watchlist CSV ↓';
 $('.table-key span').innerHTML='<i></i> Stronger watchlist evidence';
 $('#finding-text').textContent='Supplemental scouting order uses the existing within-role consensus indices, not a new cross-role talent model. No India playing-XI appearances were recorded for these candidates in the supplied dataset. Current senior Test/ODI/T20I debut status and auction availability require verification. Badoni and Suyash have the stronger evidence; the bottom three are monitoring options.';
 $$('.table-tab').forEach(b=>{const active=b.dataset.role==='uncapped';b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
}

async function init() {
  try {
    const response=await fetch('data.json');if(!response.ok)throw new Error('Data unavailable');state.data=await response.json();
    $('.rank-jumps').innerHTML=Array.from({length:10},(_,i)=>`<button aria-label="Show rank ${i+1}" aria-pressed="${i===0}" class="${i===0?'current':''}">${String(i+1).padStart(2,'0')}</button>`).join('');
    $$('.rank-jumps button').forEach((b,i)=>b.addEventListener('click',()=>jumpTo(i)));
    $$('.role-tab, .watchlist-launch').forEach(b=>b.addEventListener('click',()=>{
      if(b.dataset.role===state.role){jumpTo(0,'instant');return;}
      state.role=b.dataset.role;
      $$('.role-tab').forEach(tab=>{const active=tab.dataset.role===state.role;tab.classList.toggle('active',active);tab.setAttribute('aria-pressed',String(active));});
      renderDeck();jumpTo(0,'instant');
      $('.deck-note').innerHTML=state.role==='uncapped'?'Supplemental scouting order; cap status and availability need verification.<br>Index is relative within each discipline. Main-list checks refer to the original top tens.':'<a class="checks-link" href="#model-checks">13/13 checks = top ten in all 13 analysis versions ↗</a><br>Index ≠ probability. Auction availability is unverified.';
    }));
    $('#previous').addEventListener('click',()=>jumpTo(state.active-1));
    $('#next').addEventListener('click',()=>jumpTo(state.active+1));
    $$('.table-tab').forEach(b=>b.addEventListener('click',()=>{state.tableRole=b.dataset.role;renderTable();}));
    $('#player-search').addEventListener('input',renderTable);
    document.addEventListener('click',event=>{if(event.target.closest('.checks-link'))$('#model-checks').open=true;});
    const queue=()=>{if(state.pending)return;state.pending=true;requestAnimationFrame(()=>{state.pending=false;updateCards();});};
    window.addEventListener('scroll',queue,{passive:true});window.addEventListener('resize',queue);
    reducedMotion.addEventListener('change',()=>{renderDeck();queue();});
    renderDeck();renderTable();
    const note=document.createElement('p');note.className='fine';note.style.cssText='font-size:9px;color:#5d6276;margin-top:13px';note.textContent='* Frequency of top-10 inclusion across 1,000 whole-match resamples under the primary model; conditional on fitted expectations, not a future success probability.';$('.table-key').after(note);
    const credits=document.createElement('div');credits.innerHTML=[...state.data.batter.slice(0,10),...state.data.bowler.slice(0,10),...state.data.uncapped].filter((p,i,a)=>a.findIndex(v=>v.player_id===p.player_id)===i).map(p=>`<a href="${escapeHTML(p.photoSource)}" target="_blank" rel="noopener">${escapeHTML(p.player_name)} ↗</a>`).join('');$('#photo-credits').append(credits);
  }catch(error){$('.deck').innerHTML='<p class="load-error">Player data could not load. Please refresh or open the methodology report.</p>';console.error(error);}
}
init();
