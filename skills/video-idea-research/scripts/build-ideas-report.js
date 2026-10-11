#!/usr/bin/env node
/**
 * build-ideas-report.js — renders ideas-report.md + REPORT.html from
 * video-ideas.json (the canonical output of the video-idea-research playbook).
 *
 * Usage:
 *   node build-ideas-report.js <path-to-video-ideas.json> [--out <dir>]
 *
 * No dependencies. Writes ideas-report.md and REPORT.html next to the input
 * file (or --out dir). Schema: skills/video-idea-research/SKILL.md.
 */
'use strict';

const fs = require('fs');
const path = require('path');

function die(msg) {
  console.error(`build-ideas-report: ${msg}`);
  process.exit(1);
}

function fmtViews(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '—';
  const n = Number(v);
  if (n >= 1e6) return `${(n / 1e6).toFixed(n >= 1e7 ? 0 : 1)}M`;
  if (n >= 1e3) return `${(n / 1e3).toFixed(n >= 1e5 ? 0 : 1)}K`;
  return String(n);
}

function esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function scriptToHtml(text) {
  return esc(text || '').split('\n').map(line => {
    if (/^\[HOOK\]/.test(line)) return `<div class="ln hook">${line}</div>`;
    if (/^\[CTA\]/.test(line)) return `<div class="ln cta">${line}</div>`;
    return `<div class="ln">${line}</div>`;
  }).join('\n');
}

function hotness(n) {
  return '🔥'.repeat(Math.max(1, Math.min(5, Number(n) || 1)));
}

function buildMarkdown(d) {
  const L = [];
  L.push(`# Video Ideas — ${d.topic}`);
  L.push(`**Plataforma:** ${d.platform} · **Ventana:** ${d.window} · **Fecha:** ${d.generatedAt}`);
  L.push(`**Audiencia:** ${d.targetAudience || 'auto'} · **Idioma:** ${d.language || 'es'}`);
  L.push('');
  L.push('## 1. Top 10 videos (por vistas en la ventana)');
  L.push('');
  L.push('| # | Video | Canal | Vistas | Velocidad/día | Gancho |');
  L.push('|---|-------|-------|--------|---------------|--------|');
  (d.topVideos || []).forEach(v => {
    L.push(`| ${v.rank} | [${String(v.title || '').replace(/\|/g, '/')}](${v.url || '#'}) | ${v.channel || '—'} | ${fmtViews(v.views)} | ${fmtViews(v.velocityPerDay)} | ${v.outline && v.outline.hook ? 'ver outline' : '—'} |`);
  });
  L.push('');
  (d.topVideos || []).forEach(v => {
    const o = v.outline || {};
    L.push(`### #${v.rank} — ${v.title}`);
    L.push(`- **Canal:** ${v.channel || '—'} · **Vistas:** ${fmtViews(v.views)} · **Publicado:** ${v.publishedAt || '—'} · **URL:** ${v.url || '—'}`);
    L.push(`- **Hook:** ${o.hook || '—'}`);
    if (Array.isArray(o.beats) && o.beats.length) L.push(`- **Beats:** ${o.beats.join(' → ')}`);
    L.push(`- **CTA:** ${o.cta || '—'} · **Formato:** ${o.format || '—'} · **Duración:** ${o.durationSec ? `${o.durationSec}s` : '—'}`);
    L.push('');
  });
  L.push('## 2. Las 5 ideas de video');
  L.push('');
  (d.ideas || []).forEach(idea => {
    const y = idea.youtube || {};
    L.push(`### Idea ${idea.rank} — ${idea.title} · ${hotness(idea.hotness)} · est. ${fmtViews(idea.viewEstimate && idea.viewEstimate.min)}–${fmtViews(idea.viewEstimate && idea.viewEstimate.max)} vistas`);
    L.push(`**Ángulo:** ${idea.angle || '—'} — ${idea.whyItWins || ''}`);
    if (idea.investigation) {
      L.push('');
      L.push('#### Investigación');
      if (idea.investigation.summary) L.push(idea.investigation.summary);
      if (Array.isArray(idea.investigation.keyFacts) && idea.investigation.keyFacts.length) {
        L.push('');
        idea.investigation.keyFacts.forEach(f => L.push(`- ${f}`));
      }
      if (Array.isArray(idea.investigation.sources) && idea.investigation.sources.length) {
        L.push('');
        L.push(`**Fuentes:** ${idea.investigation.sources.join(' · ')}`);
      }
    }
    if (Array.isArray(idea.audiences) && idea.audiences.length) {
      L.push(`**Audiencias:** ${idea.audiences.map(a => `${a.segment} (${a.score}/10)`).join(' · ')}`);
    }
    L.push('');
    L.push('#### Títulos');
    [y.title, ...((idea.altTitles) || [])].filter(Boolean).forEach((t, i) => L.push(`${i + 1}. ${t}`));
    L.push('');
    const names = { viral: 'VIRAL (viral_shorts)', storytelling: 'STORYTELLING', inspiration: 'INSPIRACIÓN (motivational)' };
    ['viral', 'storytelling', 'inspiration'].forEach(k => {
      if (!idea.scripts || !idea.scripts[k]) return;
      L.push(`#### Guion ${names[k]}`);
      L.push('');
      L.push(idea.scripts[k].split('\n').map(l => `> ${l}`).join('\n'));
      L.push('');
    });
    L.push('#### Paquete YouTube');
    L.push(`- **Título:** ${y.title || '—'}`);
    L.push(`- **Descripción:** ${y.description || '—'}`);
    L.push(`- **Tags:** ${(y.tags || []).join(', ') || '—'}`);
    L.push(`- **Keywords:** ${(y.keywords || []).join(', ') || '—'}`);
    L.push('');
    if (Array.isArray(idea.sourceVideos) && idea.sourceVideos.length) {
      L.push(`**Videos fuente:** #${idea.sourceVideos.join(', #')} del top 10`);
    }
    if (Array.isArray(idea.mediaLinks) && idea.mediaLinks.length) {
      L.push('**Media:**');
      idea.mediaLinks.forEach(m => L.push(`- ${m.platform}: ${m.url}${m.description ? ` — ${m.description}` : ''}`));
    }
    L.push('');
  });
  return L.join('\n');
}

function buildHtml(d) {
  const css = `
:root{color-scheme:dark}
body{background:#0d1117;color:#e6edf3;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;margin:0;padding:24px;line-height:1.55}
.wrap{max-width:1100px;margin:0 auto}
h1{font-size:26px;margin:0 0 4px}
h2{font-size:20px;margin:32px 0 12px;border-bottom:1px solid #30363d;padding-bottom:6px}
h3{font-size:16px;margin:0 0 8px}
.meta{color:#8b949e;font-size:13px;margin-bottom:8px}
table{width:100%;border-collapse:collapse;font-size:13px;margin:12px 0}
th,td{border:1px solid #30363d;padding:6px 8px;text-align:left;vertical-align:top}
th{background:#161b22}
tr:nth-child(even) td{background:#12161d}
a{color:#58a6ff;text-decoration:none}
a:hover{text-decoration:underline}
.card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:16px 18px;margin:16px 0}
.badge{display:inline-block;background:#1f6feb33;border:1px solid #1f6feb;color:#79c0ff;border-radius:999px;padding:1px 10px;font-size:12px;margin-right:6px}
.badge.est{background:#23863622;border-color:#238636;color:#7ee787}
.chip{display:inline-block;background:#21262d;border-radius:6px;padding:1px 8px;font-size:12px;margin:2px 4px 2px 0;color:#c9d1d9}
.scripts{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;margin:12px 0}
.script{background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:10px 12px;font-size:13px}
.script h4{margin:0 0 8px;font-size:12px;letter-spacing:.08em;color:#8b949e;text-transform:uppercase}
.ln{margin:1px 0}
.ln.hook{color:#ffa657;font-weight:600}
.ln.cta{color:#7ee787;font-weight:600}
pre{white-space:pre-wrap;word-break:break-word;background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:10px 12px;font-size:12.5px;margin:8px 0}
details{margin:8px 0;background:#12161d;border:1px solid #30363d;border-radius:8px;padding:8px 12px}
summary{cursor:pointer;font-weight:600}
.foot{color:#6e7681;font-size:12px;margin-top:40px;border-top:1px solid #30363d;padding-top:12px}
`;
  const H = [];
  H.push(`<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Video Ideas — ${esc(d.topic)}</title><style>${css}</style></head><body><div class="wrap">`);
  H.push(`<h1>Video Ideas — ${esc(d.topic)}</h1>`);
  H.push(`<div class="meta">Plataforma: <b>${esc(d.platform)}</b> · Ventana: <b>${esc(d.window)}</b> · ${esc(d.generatedAt)} · Audiencia: ${esc(d.targetAudience || 'auto')} · Idioma: ${esc(d.language || 'es')}</div>`);
  H.push('<h2>1. Top 10 videos (por vistas en la ventana)</h2>');
  H.push('<table><tr><th>#</th><th>Video</th><th>Canal</th><th>Vistas</th><th>Vel./día</th><th>Gancho</th></tr>');
  (d.topVideos || []).forEach(v => {
    const hook = (v.outline && v.outline.hook) || '';
    H.push(`<tr><td>${v.rank}</td><td><a href="${esc(v.url || '#')}">${esc(v.title)}</a></td><td>${esc(v.channel || '—')}</td><td>${fmtViews(v.views)}</td><td>${fmtViews(v.velocityPerDay)}</td><td>${esc(hook.slice(0, 90))}${hook.length > 90 ? '…' : ''}</td></tr>`);
  });
  H.push('</table>');
  (d.topVideos || []).forEach(v => {
    const o = v.outline || {};
    H.push(`<details><summary>Outline #${v.rank} — ${esc(v.title)}</summary>
<p><b>Hook:</b> ${esc(o.hook || '—')}</p>
<p><b>Beats:</b> ${esc((o.beats || []).join(' → ') || '—')}</p>
<p><b>CTA:</b> ${esc(o.cta || '—')} · <b>Formato:</b> ${esc(o.format || '—')} · <b>Duración:</b> ${o.durationSec ? `${o.durationSec}s` : '—'} · <b>Publicado:</b> ${esc(v.publishedAt || '—')}</p></details>`);
  });
  H.push('<h2>2. Las 5 ideas de video</h2>');
  (d.ideas || []).forEach(idea => {
    const y = idea.youtube || {};
    const est = idea.viewEstimate || {};
    H.push(`<div class="card"><h3>Idea ${idea.rank} — ${esc(idea.title)}</h3>
<div><span class="badge">${hotness(idea.hotness)}</span><span class="badge est">est. ${fmtViews(est.min)}–${fmtViews(est.max)} vistas</span></div>
<p class="meta"><b>Ángulo:</b> ${esc(idea.angle || '—')} — ${esc(idea.whyItWins || '')}</p>`);
    if (idea.investigation) {
      const inv = idea.investigation;
      H.push('<details open><summary>Investigación</summary>');
      if (inv.summary) H.push(`<p>${esc(inv.summary)}</p>`);
      if (Array.isArray(inv.keyFacts) && inv.keyFacts.length) {
        H.push('<ul>' + inv.keyFacts.map(f => `<li>${esc(f)}</li>`).join('') + '</ul>');
      }
      if (Array.isArray(inv.sources) && inv.sources.length) {
        H.push('<p class="meta"><b>Fuentes:</b> ' + inv.sources.map(s => `<a href="${esc(s)}">${esc(s)}</a>`).join(' · ') + '</p>');
      }
      H.push('</details>');
    }
    if (Array.isArray(idea.audiences) && idea.audiences.length) {
      H.push(`<div>${idea.audiences.map(a => `<span class="chip">${esc(a.segment)} ${a.score}/10</span>`).join('')}</div>`);
    }
    const titles = [y.title, ...(idea.altTitles || [])].filter(Boolean);
    if (titles.length) {
      H.push('<p><b>Títulos:</b></p><ol>' + titles.map(t => `<li>${esc(t)}</li>`).join('') + '</ol>');
    }
    H.push('<div class="scripts">');
    const names = { viral: 'Viral · viral_shorts', storytelling: 'Storytelling', inspiration: 'Inspiración · motivational' };
    ['viral', 'storytelling', 'inspiration'].forEach(k => {
      if (!idea.scripts || !idea.scripts[k]) return;
      H.push(`<div class="script"><h4>${names[k]}</h4>${scriptToHtml(idea.scripts[k])}</div>`);
    });
    H.push('</div>');
    const meta = [`Título: ${y.title || '—'}`, `Descripción: ${y.description || '—'}`, `Tags: ${(y.tags || []).join(', ') || '—'}`, `Keywords: ${(y.keywords || []).join(', ') || '—'}`].join('\n');
    H.push(`<p><b>Paquete YouTube</b></p><pre>${esc(meta)}</pre>`);
    const links = [];
    if (Array.isArray(idea.sourceVideos) && idea.sourceVideos.length) links.push('<b>Videos fuente:</b> #' + idea.sourceVideos.join(', #'));
    if (Array.isArray(idea.mediaLinks) && idea.mediaLinks.length) links.push(idea.mediaLinks.map(m => `${esc(m.platform)}: <a href="${esc(m.url)}">${esc(m.url)}</a>${m.description ? ' — ' + esc(m.description) : ''}`).join('<br>'));
    if (links.length) H.push(`<p class="meta">${links.join('<br>')}</p>`);
    H.push('</div>');
  });
  H.push(`<div class="foot">Generado por video-idea-research · ranking por vistas dentro de la ventana · scripts: templates del backend (viral_shorts / storytelling / motivational) + hook library pública</div>`);
  H.push('</div></body></html>');
  return H.join('\n');
}

function main() {
  const args = process.argv.slice(2);
  const input = args.find(a => !a.startsWith('--'));
  if (!input) die('usage: node build-ideas-report.js <path-to-video-ideas.json> [--out <dir>]');
  const outIdx = args.indexOf('--out');
  if (!fs.existsSync(input)) die(`file not found: ${input}`);
  let data;
  try {
    data = JSON.parse(fs.readFileSync(input, 'utf8'));
  } catch (e) {
    die(`invalid JSON: ${e.message}`);
  }
  if (!data.topic || !Array.isArray(data.ideas)) {
    die('video-ideas.json must have "topic" and "ideas[]"');
  }
  const outDir = outIdx > -1 && args[outIdx + 1] ? args[outIdx + 1] : path.dirname(path.resolve(input));
  fs.mkdirSync(outDir, { recursive: true });
  const mdPath = path.join(outDir, 'ideas-report.md');
  const htmlPath = path.join(outDir, 'REPORT.html');
  fs.writeFileSync(mdPath, buildMarkdown(data));
  fs.writeFileSync(htmlPath, buildHtml(data));
  console.log(`✅ ${data.ideas.length} ideas · ${(data.topVideos || []).length} top videos`);
  console.log(`   ${mdPath}`);
  console.log(`   ${htmlPath}`);
}

main();
