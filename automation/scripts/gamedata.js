#!/usr/bin/env node
/*
 * Facts for one post date, read straight from the Play Keralam games' own data and code,
 * so a post can never disagree with what players see.
 *
 *   node gamedata.js --site <path to the Keralamtimes site checkout> --date YYYY-MM-DD [--out file.json]
 *
 * Spoiler rule: the daily games (Vaakku, Paryayam, Thaaranira, Katha) only ever give
 * YESTERDAY's puzzle relative to --date (the day the post goes out). That puzzle closed at
 * midnight IST, so revealing it gives nothing away. Today's and future answers are never output.
 */
'use strict';
const fs = require('fs');
const path = require('path');

const args = Object.fromEntries(
  process.argv.slice(2).reduce((acc, a, i, all) => (a.startsWith('--') ? [...acc, [a.slice(2), all[i + 1]]] : acc), []),
);
if (!args.site || !args.date) {
  console.error('usage: node gamedata.js --site <site checkout> --date YYYY-MM-DD [--out file.json]');
  process.exit(2);
}
const site = path.resolve(args.site);
const need = (p) => require(path.join(site, p));

const DAY = 24 * 60 * 60 * 1000;
const [Y, Mo, D] = args.date.split('-').map(Number);
const postDay = Date.UTC(Y, Mo - 1, D); // the India calendar day the post goes out
const dayNumber = (launch) => Math.floor((postDay - launch) / DAY) + 1; // puzzle number on the post day

// mulberry32, the same seeded shuffle the games use.
function shuffledOrder(n, seed) {
  let a = seed >>> 0;
  const rand = () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  const order = Array.from({ length: n }, (_, i) => i);
  for (let i = n - 1; i > 0; i--) {
    const j = Math.floor(rand() * (i + 1));
    [order[i], order[j]] = [order[j], order[i]];
  }
  return order;
}
// A deterministic random source for this date, for the non-daily picks.
let pickSeed = (Y * 10000 + Mo * 100 + D) >>> 0;
const rnd = () => {
  pickSeed = (pickSeed + 0x6d2b79f5) >>> 0;
  let t = pickSeed;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
};
const pick = (list) => list[Math.floor(rnd() * list.length)];

const out = { date: args.date, note: 'Daily-game answers are yesterday\'s (relative to date) only.' };

// ----- Vaakku (Wordle): launch 23 Sep 2026, seed 20260923, half-way offset.
{
  const WORDS = need('wordle/words.js');
  const A = need('wordle/akshara.js');
  const LAUNCH = Date.UTC(2026, 8, 23);
  const ORDER = shuffledOrder(WORDS.length, 20260923);
  const wordOn = (n) => WORDS[ORDER[(n - 1 + Math.floor(WORDS.length / 2)) % WORDS.length]];
  const n = dayNumber(LAUNCH) - 1;
  const [word, meaning] = wordOn(n);
  out.vaakku = { todayNumber: n + 1, yesterday: { n, word, meaning, aksharas: A.split(word), boxes: A.split(word).length } };
}

// ----- Paryayam: launch 1 Oct 2026; the game's own daily.js picks the round.
{
  const PUZZLES = need('paryayam/data/puzzles.js');
  const Daily = need('paryayam/daily.js');
  const n = dayNumber(Daily.LAUNCH) - 1;
  if (n >= 1) {
    const [word, english, pos, gloss, top, bonus] = PUZZLES[Daily.roundIndex(PUZZLES.length, n)];
    out.paryayam = {
      todayNumber: n + 1,
      yesterday: { n, word, english, pos, gloss, five: top.split(' ').filter(Boolean), bonusCount: bonus.split(' ').filter(Boolean).length },
    };
  }
}

// ----- Thaaranira: launch 24 Sep 2026, seed 20260924.
{
  const DATA = need('cast/films.js');
  const FILMS = DATA.films;
  const ORDER = shuffledOrder(FILMS.length, 20260924);
  const n = dayNumber(Date.UTC(2026, 8, 24)) - 1;
  const f = FILMS[ORDER[(n - 1) % FILMS.length]];
  out.thaaranira = {
    todayNumber: n + 1,
    yesterday: { n, title: f.title, year: f.year, cast: f.cast.slice(0, 10), director: f.director, genres: f.genres, rating: f.rating },
    totalFilms: FILMS.length,
  };
}

// ----- Katha: launch 24 Sep 2026; ten stories a day, band 0 easiest. Uses the game's katha.js.
{
  const DATA = need('plot/films.js');
  const K = need('plot/katha.js');
  const n = dayNumber(Date.UTC(2026, 8, 24)) - 1;
  const ten = K.dailyFilms(K.byBand(DATA.films), n);
  const easy = ten[0];
  out.katha = {
    todayNumber: n + 1,
    yesterday: {
      n,
      easiest: { title: easy.title, year: easy.year, genres: easy.genres, director: easy.director, lead: easy.lead, plot: easy.plot },
      allTen: ten.map((f) => `${f.title} (${f.year})`),
    },
  };
}

// ----- Aadyam: a pair of well-known films (both in Thaaranira's list) with exact dates, 2–12 years apart.
{
  const FIRST = need('first/films.js').films;
  const known = new Set(need('cast/films.js').films.map((f) => f.id));
  const exact = FIRST.filter((f) => known.has(f.id) && /^\d{4}-\d{2}-\d{2}$/.test(f.date));
  const t = (f) => Date.parse(f.date + 'T00:00:00Z');
  let a, b;
  for (let tries = 0; tries < 500; tries++) {
    a = pick(exact);
    b = pick(exact);
    const years = Math.abs(t(a) - t(b)) / (365.25 * DAY);
    if (a.id !== b.id && a.title !== b.title && years >= 2 && years <= 12) break;
  }
  const [first, second] = t(a) < t(b) ? [a, b] : [b, a];
  const card = (f) => ({ title: f.title, date: f.date, director: f.director, cast: f.cast.slice(0, 3) });
  out.aadyam = {
    // Shown order (top, bottom) is a and b; the answer is which came first.
    shown: [card(a), card(b)],
    first: first.title,
    gapYears: Math.round(((t(second) - t(first)) / (365.25 * DAY)) * 10) / 10,
    poolSize: FIRST.length,
  };
}

// ----- Antakshari: a common starting letter and the best-known films for it.
{
  const FILMS = need('antakshari/films.js').films; // [title, year, fame, stars, director, original?]
  const letterOf = (title) => {
    const c = title.normalize('NFD').replace(/[^A-Za-z0-9]/g, '').charAt(0).toUpperCase();
    return /[A-Z]/.test(c) ? c : '#';
  };
  const counts = {};
  for (const f of FILMS) counts[letterOf(f[0])] = (counts[letterOf(f[0])] || 0) + 1;
  const common = Object.keys(counts).filter((l) => l !== '#' && counts[l] >= FILMS.length * 0.03);
  const letter = pick(common);
  const top = FILMS.filter((f) => letterOf(f[0]) === letter).sort((x, y) => y[2] - x[2]).slice(0, 8)
    .map(([title, year, , stars, director]) => ({ title, year, stars, director }));
  out.antakshari = { letter, count: counts[letter], topFilms: top, totalFilms: FILMS.length };
}

// ----- Kerala Guesser: a district or constituency, with SVG for the blank map and the answer.
{
  const MAP = need('guesser/map.js');
  const DISTRICTS = need('guesser/districts.js');
  const ring = (r) => 'M' + r.reduce((s, v, i) => s + (i % 2 ? `,${v}` : (i ? ' ' : '') + v), '') + 'Z';
  const paths = (rings) => rings.map(ring).join(' ');
  // The map is in km on a MAP.width x MAP.height canvas; frame it on Kerala with a margin.
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const r of MAP.kerala) for (let i = 0; i < r.length; i += 2) {
    x0 = Math.min(x0, r[i]); x1 = Math.max(x1, r[i]); y0 = Math.min(y0, r[i + 1]); y1 = Math.max(y1, r[i + 1]);
  }
  const pad = 14;
  const [vx, vy, vw, vh] = [x0 - pad, y0 - pad, x1 - x0 + 2 * pad, y1 - y0 + 2 * pad].map((v) => Math.round(v * 10) / 10);
  const useConstituency = rnd() < 0.5;
  const place = useConstituency ? pick(MAP.constituencies) : pick(DISTRICTS);
  const svg = (highlight) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vx} ${vy} ${vw} ${vh}" width="${Math.round((760 * vw) / vh)}" height="760">`
    + `<rect x="${vx}" y="${vy}" width="${vw}" height="${vh}" fill="#A9D6E5" stroke="#1d1a16" stroke-width="3"/>`
    + `<path d="${paths(MAP.land)}" fill="#E9D9A6" stroke="#1d1a16" stroke-width="0.6"/>`
    + `<path d="${paths(MAP.kerala)}" fill="#7DB46C" stroke="#1d1a16" stroke-width="1.6" stroke-linejoin="round"/>`
    + (highlight ? `<path d="${paths(place.rings)}" fill="#E8452C" stroke="#1d1a16" stroke-width="1.2" stroke-linejoin="round"/>` : '')
    + '</svg>';
  // CID Moosa's run: Thiruvananthapuram to Kasaragod up the coast, through the district centres.
  const routeNames = ['Thiruvananthapuram', 'Kollam', 'Alappuzha', 'Ernakulam', 'Thrissur', 'Malappuram', 'Kozhikode', 'Kannur', 'Kasaragod'];
  const stops = routeNames.map((n) => DISTRICTS.find((d) => d.name === n)).filter(Boolean);
  const pts = stops.map((d) => d.centre.join(',')).join(' ');
  const [sx, sy] = stops[0].centre;
  const [ex, ey] = stops[stops.length - 1].centre;
  out.cidmoosaRoute = {
    stops: stops.map((d) => ({ name: d.name, ml: d.ml })),
    svg: svg(false).replace('</svg>',
      `<polyline points="${pts}" fill="none" stroke="#1d1a16" stroke-width="9" stroke-linecap="round" stroke-linejoin="round"/>`
      + `<polyline points="${pts}" fill="none" stroke="#E8452C" stroke-width="5" stroke-dasharray="10 8" stroke-linecap="round" stroke-linejoin="round"/>`
      + `<circle cx="${sx}" cy="${sy}" r="9" fill="#FFC23C" stroke="#1d1a16" stroke-width="3"/>`
      + `<circle cx="${ex}" cy="${ey}" r="9" fill="#1FA35C" stroke="#1d1a16" stroke-width="3"/></svg>`),
  };
  out.guesser = {
    level: useConstituency ? 'constituency' : 'district',
    place: { name: place.name, ml: place.ml, district: place.district || place.name, districtMl: place.districtMl || place.ml },
    mapSvg: svg(false),
    answerSvg: svg(true),
    counts: { districts: DISTRICTS.length, constituencies: MAP.constituencies.length, localBodies: 1034 },
  };
}

// ----- Ashwamedham: size of its film list.
{
  const A = need('ashwamedham/films.js');
  out.ashwamedham = { films: (A.films || []).length };
}

const json = JSON.stringify(out, null, 2);
if (args.out) fs.writeFileSync(args.out, json);
else process.stdout.write(json + '\n');
