# Play Keralam Instagram: the daily reel run

On Monday, Wednesday, Friday and Saturday mornings (about 8:10 India time) a fresh Claude session runs this
playbook. It makes **one voiced reel** for **@playkeralam** and schedules it to go out at **9:00 pm the same
day**, fully automatically: no drafts, no approval. Abr (the owner) only gets the summary at the end. Work through the steps in
order. If a step fails, fix it and carry on; if the reel can't be made, say which step failed and why.

Times are India time (Asia/Calcutta). "Today" is the day the run starts, and it is also the day the reel
goes out. There are **only reels** now: no carousels or image posts.

## The rules that never bend

- **The brand is Play Keralam (പ്ലേ കേരളം), the site is playkeralam.com, the handle is @playkeralam.**
  Never write "Keralam Times", "keralamtimes" or any pages.dev address, in images, captions or speech.
- **No spoilers.** Daily games (Vaakku, Paryayam, Thaaranira, Katha) may only show **yesterday's** puzzle
  relative to the day the reel goes out. `gamedata.js` only ever gives that one. Never work out, show or
  hint at today's or a future answer.
- **Only true facts.** Everything about a game comes from `games.json` or `facts.json` (made from the
  games' own data). Don't invent features, numbers, scores or quotes.
- **Malayalam first**, natural and warm, the way people in Kerala talk online. A short English line follows
  in the caption. Write proper Malayalam Unicode (atomic chillus such as ൻ ർ ൽ ൾ ൺ).
- **5 hashtags at most** (an Instagram limit), always including #PlayKeralam.
- **One reel per run, at 9:00 pm today.** The Metricool free plan allows 20 posts a month; `plan_week.py`
  checks that.
- **Reel pace: lively, like a normal Instagram reel.** The voice is not slow and not rushed: short, punchy
  lines, a new scene every 3-5 seconds, and a short breath (about half a second) after each line so a scene
  never cuts off the instant the last word ends. The voice is sped up for you in `voice.py`; don't fight it
  by writing long sentences.
- **Fully automatic**: `autoPublish: true`, `draft: false`. Don't wait for anyone.

## 1. Set up (about 5 minutes)

1. Attach the two repositories with `add_repo` and clone each exactly as its result says:
   - `abrahamAbY09/playkeralam-media` with `access: "push"` (this repo; media and this playbook).
   - `abrahamAbY09/Keralamtimes` with `access: "read"` (the games' code and data; private, read only).
2. In the Keralamtimes clone, use the site branch: `config.json` → `repos.site.branchHint`. Fetch it with
   `git fetch --depth 1 origin <branch>` and check out `FETCH_HEAD` into a worktree, say `../site`.
   If that branch is gone, list branches with `git ls-remote --heads origin`, fetch each with depth 1 and
   use the one that has both `index.html` and `cast/films.js` and the newest commit.
3. `bash automation/scripts/setup.sh` (fonts, the voice runtime, the two Malayalam voices).
   Run every script with plain `python3`, the same one setup.sh printed ("using Python ... at ..."). setup.sh
   installs with `python3 -m pip`, so packages always go to that interpreter. Do not call `pip` or another
   `python3.x` directly. If the Playwright package and the pre-installed Chromium are different versions, the
   scripts fall back to the Chromium already on the machine (see `launch_chromium` in `common.py`); nothing to do.
4. Work in `automation/work/<today>/` (git-ignored). Write scratch files there.

## 2. Plan today's reel

```
python3 automation/scripts/plan_week.py plan-day --run-date <today> > automation/work/<today>/plan.json
```

- Exit code 3 / `"skip"`: nothing to do today (not a reel day, or today already has an entry in
  `rotation.json`, for example a post scheduled earlier by hand). Stop and report that; do nothing else.
- Also call Metricool `getScheduledPosts` (brandId `7540170`, today 00:00 to 23:59, timezone Asia/Calcutta).
  If a post is already at 9 pm today, don't schedule a second one; say so and stop.
- If `overLimit` is not empty, stop and report it; don't schedule.
- **Time check.** Ask for the current India time. The reel must be scheduled for 9:00 pm today, so if
  it is already past 8:45 pm, don't schedule in the past: report it and stop.

The plan has one item with `date`, `kind` (always reel), `topic` (a game id from `games.json`, or
`general:<name>`), `format` and `folder`.

## 3. Make the reel

In its own folder `automation/work/<today>/<folder>/`:

1. **Facts**: `node automation/scripts/gamedata.js --site <site> --date <item.date> --out facts.json`.
2. **Screenshot** (when the recipe uses one and the game has a `shot` path in games.json):
   `python3 automation/scripts/shoot.py --site <site> --date <item.date> --page <shot path> --out shot.png`
   (the front page is `--page /`). It shows the day before the reel, in Malayalam, with the help box closed.
3. **Spec**: write `spec.json` following the *Reel scenes* column of the recipe table (below) and the scene
   types documented at the top of `render_reel.py`.
4. **Render**: `python3 automation/scripts/render_reel.py spec.json out` (about 2-3 minutes).
5. **Look at it.** Read `out/contact-sheet.jpg` as an image. Check: the Malayalam reads correctly with no broken
   letters, nothing overlaps or is cut off, the facts match facts.json, no spoiler, the brand is right.
   A renderer `WARNING` that text "still overflows" or content is "taller than the slide" must be fixed
   (shorter text, fewer items); "shrank a lot" is fine if it still reads well on a phone. The renderer prints
   the reel's length: it must be 22-38 seconds, so lengthen or shorten the `say` lines if it is outside.
   Re-render until it is clean. (Rendering takes a few minutes; this is why the run starts in the morning.)
6. **Caption**: write `out/caption.txt` (see *Captions*).
7. **Check**: `python3 automation/scripts/check.py out` must pass.

### Recipes (reels: 5-7 scenes, 25-35 seconds)

Puzzle formats show the puzzle, then the answer in the next scene, then how the game plays and the call to
play. Use the facts exactly. `#N` is the puzzle number from facts (yesterday's). The *Post slides* column is
kept for reference only; **we only make reels now**, so use the *Reel scenes* column.

| Format | Post slides | Reel scenes |
| --- | --- | --- |
| vaakku `yesterday-word` | hero (kicker "ഇന്നലത്തെ വാക്ക് കിട്ടിയോ?", title "വാക്ക് #N") · tiles (clue = meaning; first box green, rest blank) · answer (big word, all-green tiles, transliteration · meaning) · screen (/wordle/, 3 points from games.json facts) · cta | hook · tiles · text "കിട്ടിയോ?" with sub "3 · 2 · 1" · answer · screen · cta |
| vaakku `how-to-play` | hero · screen · steps (3) · list (colours) · cta | hook · screen · steps · cta |
| vaakku `streak-awards` | hero · list (the four awards with days) · screen · cta | hook · list as text scenes · cta |
| paryayam `yesterday-synonyms` | hero ("ഇന്നലത്തെ വാക്ക്: <word>") · tiles (5 blank tiles, sub = English sense) · answer (five synonyms as tiles) · screen (/paryayam/) · cta | hook · tiles · text "കിട്ടിയോ?" · answer · cta |
| thaaranira `cast-puzzle` | hero · cast (first 3 names, hidden 2) · answer (title (year), director, genres · IMDb) · screen (/cast/) · cta | hook · cast (first 4, hidden 1) · text countdown · answer · screen · cta |
| katha `story-puzzle` | hero · story (the plot with ███, under 330 characters; cut whole sentences) · answer (title, year, director, lead) · screen (/plot/) · cta | hook · story · text countdown · answer · cta |
| aadyam `which-first` | hero · pair (no dates) · pair (showDates, firstIndex = the first) · screen (/first/) · cta | hook · pair · text countdown · pair with dates · cta |
| ashwamedham `challenge` / `how-it-works` | hero · steps (think, answer, it names it) · screen (/ashwamedham/) · list (facts) · cta (question: "Did it get your film?") | hook · steps · screen · cta |
| antakshari `letter-challenge` | hero (letter) · list ("Name five films starting with <L>") · answer (big letter, details = top 5 films with years) · screen (/antakshari/) · cta | hook · text challenge · answer · cta |
| kerala-guesser `where-is-it` | hero · map (svg = facts.guesser.mapSvg, place = Malayalam + English name) · answer (svg = answerSvg, big = place) · screen (/guesser/) · cta | hook · map · text countdown · answer · cta |
| kerala-guesser `levels` | hero · list (three levels with counts) · screen · cta | hook · list scenes · screen · cta |
| thurupp `how-to-play-28` / `play-with-friends` | hero · steps or list (facts) · screen (/thurupp/public/) · cta | hook · steps · screen · cta |
| cidmoosa `gadgets` / `route` | hero · list (gadgets) or map (svg = facts.cidmoosaRoute.svg, place "തിരുവനന്തപുരം → കാസർഗോഡ്") · list (facts) · cta | hook · map · text scenes · cta |
| sat `the-tharavad` / `how-to-play` | hero · list (the tharavad and its hiding places) · steps (count, hide, race and shout SAT!) · cta | hook · list · steps · cta |
| general `daily-four` | hero (game null) · logos (games = the four, highlight all) · screen (front page /) · list (new at midnight, streaks, a lamp for each) · cta | hook · logos · screen · cta |
| general `front-page` | hero · screen (/) · list (the Pooram, both calendars) · cta | hook · screen · cta |
| general `streaks` | hero · list (awards) · logos (four daily) · cta | hook · list · cta |
| general `weekend-challenge` | hero · logos (four daily) · steps (play all four, screenshot, comment) · cta | hook · logos · steps · cta |
| general `all-games` | hero · logos (all) · list (free, no ads, no login, Malayalam and English, phone and computer) · cta | hook · logos · cta |

A general item has `"game": null` in the spec.

### Reel voice-over

- Every scene has a `say` line: **Malayalam script only**. Transliterate names and film titles
  (Kumbalangi Nights → കുമ്പളങ്ങി നൈറ്റ്സ്, Mohanlal → മോഹൻലാൽ). Spell numbers as Malayalam words
  or leave them out. Latin letters and digits come out garbled.
- Keep each line short (8-14 words). The whole reel: about 60-85 words, 25-35 seconds. The voice now
  speaks at roughly 2 words a second, so the old line lengths still fit.
- The voice alternates by week on its own; don't set `voice`. Set `"date"` to the item's date.
- The last scene's `say` invites people: "പ്ലേ കേരളം ഡോട്ട് കോമിൽ സൗജന്യമായി കളിക്കൂ. ലിങ്ക് ബയോയിൽ ഉണ്ട്."
- Open with the hook in the first second (no slow intro) and keep the energy up to the last scene.

### Captions

```
<Malayalam hook, one line>

<1-2 Malayalam lines: what's in the reel, or the puzzle question>

<English, 1-2 short lines saying the same>
<A question to comment on> and <a "send this to ..." line>

ലിങ്ക് ബയോയിൽ · Link in bio · playkeralam.com

#PlayKeralam #... (5 in all, from config.json captions.tagPool, matched to the topic)
```

Puzzle reels must not give the answer in the caption. Keep it under about 900 characters.

Never write `#` before a number in a caption (no `#22`). `check.py` counts it as a hashtag and fails the caption
at 6 tags, and Instagram would treat it as one too. Write the puzzle number as `നമ്പർ 22` (or `No. 22`). The `#N`
in the recipes below is for the on-screen text inside the reel only.

## 4. Publish the media

1. Copy `reel.mp4` and `cover.jpg` into the repo at `<folder>/`. Don't commit `automation/work/`.
2. Commit ("Reel for <today>") and push to `main`.
3. Check each file's public link answers 200 with the right size:
   `https://raw.githubusercontent.com/abrahamAbY09/playkeralam-media/main/<folder>/<file>`
   (curl it from the shell; give it a minute after the push if the first try is 404).

## 5. Schedule in Metricool

Call `createScheduledPost` with `blogId` `"7540170"` and `date` `"<today>T21:00:00+05:30"`.
`info` is a JSON string:

```json
{"autoPublish": true, "draft": false, "text": "<caption.txt>",
 "media": ["<raw link to reel.mp4>"],
 "providers": [{"network": "instagram"}],
 "publicationDate": {"dateTime": "<today>T21:00:00", "timezone": "Asia/Calcutta"},
 "videoCoverMilliseconds": <coverMs from out/reel.json>,
 "instagramData": {"type": "REEL", "showReelOnFeed": true, "isAiGenerated": true},
 "shortener": false, "smartLinkData": {"ids": []}, "descendants": [], "firstCommentText": "", "hasNotReadNotes": false}
```

Keep the result's `uuid` and `plannerUrl`. If the call fails, read the error, fix what it says (wrong
format, too many hashtags, a link not yet live) and try once more; if it fails again, report it.

## 6. Record and report

1. Write `results.json`: `[{"slot": 0, "date": "<today>", "metricoolUuid": "...", "plannerUrl": "...", "folder": "...", "title": "<short description>"}]`, then
   `python3 automation/scripts/plan_week.py record --plan plan.json --results results.json`.
2. Commit `automation/rotation.json` ("Rotation after <today>") and push.
3. Call `getScheduledPosts` for today and confirm the reel is there at 9 pm, `autoPublish` true and not a draft.
4. **Show the reel in this chat.** Send `reel.mp4` with `SendUserFile` so Abr can watch it right in this run's
   chat. Then, if the harness gives you this session's own address (it appears in your commit-attribution
   instructions as `https://claude.ai/code/session_...`), include it.
5. Finish with a short summary for Abr:
   - what goes out tonight (topic, format, the caption's first line) and that it is set for 9:00 pm;
   - **where to watch it**: this chat's address (if you have it), the reel's public link
     (`https://raw.githubusercontent.com/abrahamAbY09/playkeralam-media/main/<folder>/reel.mp4`) and the Metricool planner link;
   - anything that failed or looked off. No other questions; nothing needs his OK.
