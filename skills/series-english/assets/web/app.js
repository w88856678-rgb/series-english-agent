const $ = id => document.getElementById(id);
const storageKey = 'series-english-progress-v1';
let catalog, ci = 0, wi = 0, hidden = false, records = Object.create(null), loop = false, generation = 0, timer, speaking;
const synth = window.speechSynthesis;
const current = () => catalog.courses[ci];
const word = () => current().words[wi];
const key = (c = current(), w = word()) => `${c.id}::${w.key}`;
function report(message) { $('error').textContent = message; $('error').hidden = !message; }
function save() {
  try { localStorage.setItem(storageKey, JSON.stringify({schemaVersion:1, records})); $('save-status').textContent = '进度已保存在此浏览器'; }
  catch { $('save-status').textContent = '无法保存，请立即导出进度备份'; }
}
function validRecords(data) {
  if (data?.schemaVersion !== 1 || !data.records || typeof data.records !== 'object' || Array.isArray(data.records)) throw Error('无效的进度文件');
  const out = Object.create(null);
  const pairs = Object.entries(data.records);
  if (pairs.length > 50000) throw Error('进度文件过大');
  for (const [k,v] of pairs) {
    if (!k.includes('::') || k.length > 600 || !v || !['known','review'].includes(v.status) || !Number.isFinite(v.due) || !Number.isFinite(v.updatedAt) || !Number.isInteger(v.streak) || v.streak < 0 || v.streak > 100) throw Error('进度字段无效');
    out[k] = {status:v.status,due:v.due,streak:v.streak,updatedAt:v.updatedAt};
  }
  return out;
}
function mark(status) {
  const old = records[key()], now = Date.now();
  const streak = status === 'known' ? Math.min((old?.streak || 0) + 1, 100) : 0;
  records[key()] = {status, streak, updatedAt:now, due:status === 'review' ? now : now + [1,3,7,14,30][Math.min(streak-1,4)] * 86400000};
  save(); render();
}
function dueWords() {
  return catalog.courses.flatMap((c,cidx) => c.words.flatMap((w,widx) => {
    const r = records[key(c,w)];
    return r && (r.status === 'review' || r.due <= Date.now()) ? [{ci:cidx,wi:widx}] : [];
  }));
}
function stop() { generation++; clearTimeout(timer); loop = false; synth?.cancel(); speaking = null; $('play-status').textContent = ''; $('auto').textContent = '♫ 连续跟读'; }
function voices() {
  const selected = $('voice').value;
  const list = (synth?.getVoices() || []).filter(v => /^en(?:-|_)/i.test(v.lang));
  $('voice').replaceChildren();
  for (const v of list) { const option = document.createElement('option'); option.value = v.voiceURI; option.textContent = `${v.name} · ${v.lang}`; $('voice').append(option); }
  if (list.some(v => v.voiceURI === selected)) $('voice').value = selected;
  else { const preferred = list.find(v => /Samantha|Google US English|Aria|Jenny/i.test(v.name) && /^en-US$/i.test(v.lang)) || list.find(v => v.default && /^en-US$/i.test(v.lang)) || list.find(v => /^en-US$/i.test(v.lang)); if (preferred) $('voice').value = preferred.voiceURI; }
  if (!list.length) { const o = document.createElement('option'); o.textContent = '暂无英语语音'; $('voice').append(o); }
}
function play(kind, continuous = false) {
  if (!continuous) stop();
  const selected = (synth?.getVoices() || []).find(v => v.voiceURI === $('voice').value);
  if (!synth || !selected) { stop(); report('当前浏览器没有可用英语语音。请安装系统英语声音，或换用支持语音的浏览器。'); return; }
  report('');
  const token = generation;
  const u = new SpeechSynthesisUtterance(word()[kind]);
  u.voice = selected; u.lang = selected.lang; u.rate = Number($('rate').value);
  speaking = u; $('play-status').textContent = '正在播放…';
  u.onend = () => {
    if (token !== generation) return;
    $('play-status').textContent = ''; speaking = null;
    if (continuous && loop) timer = setTimeout(() => {
      if (token !== generation) return;
      if (kind === 'term') play('sentence',true);
      else if (wi + 1 < current().words.length) { wi++; render(); play('term',true); }
      else stop();
    }, kind === 'term' ? 400 : 2400);
  };
  u.onerror = () => { if (token === generation) { stop(); report('发音未完成，请重新播放。'); } };
  synth.speak(u);
}
function choose(c,w) { stop(); ci=c; wi=w; hidden=false; report(''); render(); }
function render() {
  const c = current(), w = word();
  $('course').value = String(ci);
  $('series').textContent = c.series; $('title').textContent = c.title;
  $('eyebrow').textContent = `${c.seriesId.toUpperCase()} / S${String(c.season).padStart(2,'0')} E${String(c.episode).padStart(2,'0')}`;
  const repeats = c.words.filter(x=>x.review).length;
  $('summary').textContent = `${c.words.length} 个表达 · ${c.words.length-repeats} 个新词 · ${repeats} 个复习词`;
  $('position').textContent = `EXPRESSION ${String(wi+1).padStart(2,'0')} / ${c.words.length}`;
  const first = catalog.courses.find(x=>x.id===w.firstEpisode);
  $('repeat').textContent = w.review ? `复习词 · 首次收录 S${first?.season}E${first?.episode}` : '本剧新词';
  for (const name of ['term','sentence']) $(name).textContent = w[name];
  $('ipa').textContent = `/${w.ipa}/`;
  for (const name of ['meaning','translation','tip']) $(name).textContent = hidden ? '中文已隐藏，试着回忆一下' : w[name];
  $('hide').textContent = hidden ? '◉ 显示中文' : '◉ 隐藏中文'; $('hide').setAttribute('aria-pressed',String(hidden));
  $('prev').disabled = wi===0; $('next').disabled = wi===c.words.length-1;
  for (const s of ['review','known']) $(s).setAttribute('aria-pressed',String(records[key()]?.status===s));
  $('source').textContent = `来源：${c.source}。复习标记按已导入课程的季、集顺序计算，例句为原创。`;
  const count = c.words.filter(x=>records[key(c,x)]?.status==='known').length;
  $('count').textContent = `${count} / ${c.words.length} 已掌握`;
  $('words').replaceChildren();
  c.words.forEach((x,i)=> { const b=document.createElement('button'); b.className=i===wi?'active':''; b.textContent=`${String(i+1).padStart(2,'0')}  ${x.term}`; if(x.review){const s=document.createElement('small');s.textContent='复习';b.append(s);}b.onclick=()=>choose(ci,i);$('words').append(b); });
  const due=dueWords(); $('due').textContent=`当前有 ${due.length} 个待复习或已到复习时间的表达。`; $('due-next').disabled=!due.length;
}
async function boot() {
  if (location.protocol === 'file:') {
    $('title').textContent='请从学习网址打开';
    report('直接双击 HTML 无法加载课程。请先启动课程库，再打开 http://127.0.0.1:8765/。具体启动方法见项目 README。');
    document.querySelectorAll('button,select,input').forEach(e=>e.disabled=true);
    $('card').hidden=true;
    return;
  }
  try {
    const response=await fetch('./catalog.json'); if(!response.ok) throw Error('课程库读取失败');
    catalog=await response.json();
    if(!catalog.courses?.length){$('title').textContent='你的下一集，从这里开始';report('课程库还没有课程。请让学习 Agent 导入字幕并添加课程，或使用 --demo 创建示例库。');document.querySelectorAll('button,select').forEach(e=>e.disabled=true);$('card').hidden=true;return;}
    try { const raw=localStorage.getItem(storageKey); if(raw) records=validRecords(JSON.parse(raw)); } catch { $('save-status').textContent='未能读取保存记录；导入备份可恢复'; }
    catalog.courses.forEach((c,i)=>{const o=document.createElement('option');o.value=i;o.textContent=`${c.series} · S${c.season}E${c.episode} · ${c.title}`;$('course').append(o);});
    $('course').onchange=()=>choose(Number($('course').value),0);
    $('hide').onclick=()=>{hidden=!hidden;render();};
    $('prev').onclick=()=>choose(ci,wi-1); $('next').onclick=()=>choose(ci,wi+1);
    $('known').onclick=()=>mark('known'); $('review').onclick=()=>mark('review');
    $('speak-term').onclick=()=>play('term'); $('speak-sentence').onclick=()=>play('sentence');
    $('auto').onclick=()=>{if(loop){stop();return;}stop();loop=true;$('auto').textContent='Ⅱ 停止跟读';play('term',true);};
    $('voice').onchange=stop; $('rate').onchange=stop;
    $('due-next').onclick=()=>{const due=dueWords();const p=due.find(x=>x.ci!==ci||x.wi!==wi)||due[0];if(p)choose(p.ci,p.wi);};
    $('export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify({schemaVersion:1,records},null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='series-english-progress.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
    $('import').onchange=async e=>{try{const f=e.target.files[0];if(!f)return;if(f.size>10_000_000)throw Error('进度文件过大');const incoming=validRecords(JSON.parse(await f.text()));for(const [k,v] of Object.entries(incoming)){if(!records[k]||v.updatedAt>records[k].updatedAt)records[k]=v;}save();render();report('');}catch(err){report(err.message);}finally{e.target.value='';}};
    voices(); synth?.addEventListener('voiceschanged',voices); window.addEventListener('pagehide',stop); render();
  } catch(err){$('title').textContent='课程未能加载';report(`无法打开课程：${err.message}。请确认启动的是已初始化的课程库，然后刷新重试。`);}
}
boot();
