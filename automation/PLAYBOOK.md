# Play Keralam Instagram: the daily reel run

Every morning (about 8:10 India time) a fresh Claude session runs this playbook. On a **posting day** it
makes **one voiced reel** for **@playkeralam** and schedules it to go out at **9:00 pm the same day**, fully
automatically: no drafts, no approval. Posting days are listed month by month in `config.json` →
`daily.postDates`. Abr's rule (23 Oct 2026), made to fit Metricool's free plan of 20 published posts a month:
every Tuesday, Thursday, Saturday and Sunday, plus what the cap leaves spread evenly over Mondays, Wednesdays
and Fridays through the month. On any other day the run stops at step 2. Abr (the owner) only gets the summary at the end. Work through the steps in
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
- **One reel per posting day, at 9:00 pm today.** The Metricool free plan publishes at most 20 posts a
  calendar month; the posting calendar is built to stay within it, and `plan_week.py` checks it too.
- **Every reel follows the approved style** in *Reel style* below (Abr signed it off on 23 Oct 2026):
  hook first, fast, items synced to the voice, proper conjuncts. The model is
  `automation/examples/thaaranira-cast-puzzle.json`; copy its shape.
- **Fully automatic**: `autoPublish: true`, `draft: false`. Don't wait for anyone.

## Reel style (approved by Abr, 23 Oct 2026)

These are his three requirements, plus what made the approved sample work. Don't loosen them.

1. **Open with something catchy, then follow up.** The first scene is always a `hook`: a challenge or
   question about the puzzle, in 1-3 huge, short lines, already on screen at frame 0 and over within about
   2.5 seconds. Then the follow-up (the clues, the puzzle), then the reveal. Good hooks:
   "4 സൂചന · 1 സിനിമ · എത്ര സൂചനയിൽ പറയും?", "3 അക്ഷരം · അർത്ഥം: sand · ഇന്നലത്തെ വാക്ക് പറയാമോ?",
   "ഏത് പടമാണ് ആദ്യം? · A ഓ B ഓ?". Write a fresh hook for each reel in that spirit. Never open with a logo
   alone, a greeting ("ഹലോ ഫ്രണ്ട്സ്"), the site name, or a slow intro. Hooks must be true: no invented
   statistics or claims ("90% പേർക്കും തെറ്റും" is not allowed).
2. **Pace: fast, about twice the first reels.** The voice speed is fixed in `voice.py` (Abr tried "twice as
   fast", found it slightly too fast, and approved this setting; don't change it). Your part: one idea per
   beat, 2-8 words per voice line, no filler. The renderer places lines back to back with a 0.14 s gap and
   cuts each scene 0.38 s after its last line. A reel is **12-22 seconds** (the model is 14.4 s), 5-7 scenes,
   about 30-45 spoken words.
3. **Proper Malayalam conjuncts (കൂട്ടക്ഷരങ്ങൾ).** On-screen text must show ക്ക ട്ട ന്ന ത്ത ങ്ങ ണ്ട ഡ്ഡ ക്ഷ
   and the rest as joined letters, never as two letters with a visible chandrakkala (ക്‌ക). The cause was
   `<html lang="ml">`: with it, Baloo Chettan 2 switches to reformed-script forms and splits every conjunct.
   The renderers no longer set it; never add it back. Don't type zero-width non-joiners (U+200C); the
   renderer strips them. Check the frames for split conjuncts every time.
4. **Sync.** Every on-screen item lands the moment its voice line starts (that's what a beat is): cast
   names, steps, tiles, the answer. Nothing sits on screen waiting for the voice, and the voice never talks
   about something not yet shown.
5. **Shape:** hook → the puzzle or content (one item per beat) → a short countdown ("കിട്ടിയോ?" 3·2·1) when
   there's an answer to reveal → the reveal with a comment question ("എത്രാമത്തെ സൂചനയിൽ കിട്ടി? കമന്റ്
   ചെയ്യൂ!") → the CTA. Sounds (boom, pops, ticks, the reveal ding, whooshes between scenes) and the 124 bpm
   music bed are added by the renderer.

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

- Exit code 3 / `"skip"`: no reel today. Either today isn't a posting day in `daily.postDates`, or today's
  reel is already made (`rotation.json` has a daily-run entry for today). Stop and report it in one line;
  do nothing else. If the skip says the month has **no posting calendar yet**, also send a push notification
  telling Abr the calendar has run out and needs extending (`plan_week.py calendar --month YYYY-MM` builds a
  month by his rule). Posts left from the old weekly run (26, 28, 30 and 31 Oct 2026) do **not** block a
  posting day: a second post on those days is fine.
- Also call Metricool `getScheduledPosts` (brandId `7540170`, today 00:00 to 23:59, timezone Asia/Calcutta).
  If a REEL at 9 pm today was **created today** (its `creationDate` is today), this routine already
  scheduled it: don't schedule a second one; say so and stop. Any other post at 9 pm today (one scheduled
  on an earlier day) is fine: schedule today's reel as usual.
- If `overLimit` is not empty, stop and report it; don't schedule. The posting calendar keeps each month at
  20 posts at most (Metricool's free plan cap), so this only happens if extra posts were added by hand.
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
3. **Spec**: write `spec.json` in beats, following the recipe for today's format (below), the scene types at
   the top of `render_reel.py`, and the shape of `automation/examples/thaaranira-cast-puzzle.json` (read it
   first, every run). Copy screenshots into this folder and refer to them by file name (`"shot": "shot.png"`).
4. **Render**: `python3 automation/scripts/render_reel.py spec.json out` (about a minute).
5. **Look at it.** Read `out/contact-sheet.jpg` (a frame after every beat) and `out/cover.jpg` (the end of the
   hook) as images. Check:
   - the hook is the first thing on screen and reads as a question or challenge;
   - **every conjunct is joined**: zoom in (crop a frame at full size) if the text is small; any ക്‌ക-style
     split means something re-added `lang="ml"` or a U+200C; fix it, don't post it;
   - nothing overlaps or is cut off, every item appears with its line, the facts match facts.json, no
     spoiler, the brand is right.
   Every renderer `WARNING` must be fixed (it flags Latin letters or digits in a voice line, long voice
   lines, content outside the safe area, a first scene that isn't a hook, and a length outside 12-22 s).
   Re-render until it is clean.
6. **Caption**: write `out/caption.txt` (see *Captions*).
7. **Check**: `python3 automation/scripts/check.py out` must pass.

### Recipes (reels: 5-7 scenes, 12-22 seconds, hook first)

`#N` is the puzzle number from facts (yesterday's) and is fine on screen; in a `say` line write the number as a
Malayalam word or leave it out. The hooks are starting points: write a fresh one each time, true and short.
"Countdown" means the `countdown` scene exactly as in the model reel. The CTA is always the last scene
(`shot` of the game's page when the recipe has one, else no shot), with "side" a two-line true fact from
games.json, and its last beat says "പ്ലേ കേരളം ഡോട്ട് കോമിൽ സൗജന്യമായി കളിക്കൂ!".

| Format | Hook (scene 1) | Then (one item per beat) |
| --- | --- | --- |
| thaaranira `cast-puzzle` | "4 സൂചന" · "1 സിനിമ" · tag "എത്ര സൂചനയിൽ പറയും?" | **the model reel, exactly**: clues (headline "ഏതാ പടം?", first 4 cast names in IMDb order, transliterated, one per beat, hidden 1) · countdown · answer (kicker "ഉത്തരം", big = title in Malayalam, chips year + "IMDb x.x", detail = director; 2nd beat question "എത്രാമത്തെ സൂചനയിൽ കിട്ടി? കമന്റ് ചെയ്യൂ!") · cta (shot /cast/) |
| thaaranira `how-to-play` | "താരനിര" · tag "പേര് കേട്ട് പടം പറയാമോ?" | steps (the 3 facts, short) · screen (/cast/) · cta |
| vaakku `yesterday-word` | "N അക്ഷരം" · mid "അർത്ഥം: <meaning>" · tag "ഇന്നലത്തെ വാക്ക് പറയാമോ?" | tiles (headline "വാക്ക് #N", first box green with the first akshara, rest blank; sub = meaning) · countdown · answer (big = word, tiles = all aksharas green; question "എത്രാമത്തെ ശ്രമത്തിൽ കിട്ടി? കമന്റ് ചെയ്യൂ!") · cta (shot /wordle/) |
| vaakku `how-to-play` | "മലയാളം വേർഡിൽ!" · tag "കളിച്ചിട്ടുണ്ടോ?" | steps (3, from facts) · cards, not numbered (the colours) · cta (shot) |
| vaakku `streak-awards` | "ദിവസവും കളിച്ചാൽ?" · tag "സമ്മാനം!" | cards (the four awards with days, one per beat) · text (question "നിങ്ങളുടെ സ്ട്രീക്ക് എത്ര?") · cta |
| paryayam `yesterday-synonyms` | big = the word · mid "5 പര്യായങ്ങൾ" · tag "എത്രയെണ്ണം അറിയാം?" | tiles (5 blank tiles, sub = English sense) · countdown · answer (big = word, tiles = the five, green; question "എത്രയെണ്ണം കിട്ടി? കമന്റ് ചെയ്യൂ!") · cta (shot /paryayam/) |
| katha `story-puzzle` | "ഒറ്റ വരി കഥ" · tag "ഏതാ പടം?" | story (the plot as one Malayalam sentence, faithful to facts, ███ kept, under 140 characters, "min": 3.2) · countdown · answer (title, chips year + director, detail = lead; question "കഥ കേട്ട് കിട്ടിയോ?") · cta (shot /plot/) |
| aadyam `which-first` | mid "ഏത് പടമാണ് ആദ്യം?" · tag "A ഓ B ഓ?" | pair (no dates; beat 1 says film A, beat 2 film B) · countdown · pair (showDates, firstIndex; a "reveal" beat "<first> ആദ്യം!") · text (question "നിങ്ങൾ ശരിയാക്കിയോ? കമന്റ് ചെയ്യൂ!") · cta (shot /first/) |
| ashwamedham `challenge` / `how-it-works` | "ഒരു പടം മനസ്സിൽ വിചാരിക്കൂ" (mid) · tag "അശ്വമേധം കണ്ടുപിടിക്കും!" | steps (think, answer, it names it) · screen (/ashwamedham/) · cta (side "നിങ്ങളുടെ പടം\nകിട്ടിയോ?") |
| antakshari `letter-challenge` | big = the letter · mid "5 പടങ്ങൾ" · tag "പറയാമോ?" | countdown · cards (numbered: the top 5 films with years, transliterated, one per beat) · text (question "നിങ്ങൾ എത്ര പറഞ്ഞു? കമന്റ് ചെയ്യൂ!") · cta (shot /antakshari/) |
| kerala-guesser `where-is-it` | big = the place name (facts.guesser.place.ml) · mid "മാപ്പിൽ എവിടെ?" · tag "ഒറ്റ നോട്ടത്തിൽ പറയാമോ?" | The game names a place and you find it on a blank map. map (headline "എവിടെയാണ് <place>?", svg = facts.guesser.mapSvg (blank), place = the level in Malayalam, e.g. "നിയമസഭാ മണ്ഡലം"; beats: the level, then "വടക്കോ, മധ്യത്തിലോ, തെക്കോ?" with "place": true) · countdown · answer (kicker "ഇവിടെ!", big = place, svg = answerSvg (the renderer rings the red spot), chips "<district> ജില്ല"; beat 1 "<district> ജില്ലയിൽ!", beat 2 question "എത്ര അടുത്തെത്തി? കമന്റ് ചെയ്യൂ!") · cta (shot /guesser/, side "140 മണ്ഡലങ്ങൾ\n1,034 തദ്ദേശങ്ങൾ") |
| kerala-guesser `levels` | "കേരളം എത്ര അറിയാം?" · tag "മൂന്ന് ലെവൽ!" | cards (three levels with counts) · screen (/guesser/) · cta |
| thurupp `how-to-play-28` / `play-with-friends` | "ഇരുപത്തെട്ട് കളിക്കാം!" (mid) · tag "ആളെ കൂട്ടിക്കോ!" | steps or cards (facts) · screen (/thurupp/public/) · cta |
| cidmoosa `gadgets` / `route` | "സി.ഐ.ഡി. മൂസ" · tag "ഗെയിം കളിച്ചോ?" | map (svg = facts.cidmoosaRoute.svg, place "തിരുവനന്തപുരം → കാസർഗോഡ്") or cards (gadgets) · cards (facts) · cta |
| sat `the-tharavad` / `how-to-play` | "സാറ്റ്!" · tag "ഒളിച്ചുകളി ഓർമ്മയുണ്ടോ?" | cards (the tharavad and its hiding places) · steps (count, hide, race and shout SAT!) · cta |
| general `daily-four` | "4 കളികൾ" · mid "ദിവസവും പുതിയത്" · tag "ഇന്ന് എത്ര കളിച്ചു?" | logos (the four, highlight all) · screen (front page /) · cta |
| general `front-page` | "11 കളികൾ" · tag "എല്ലാം ഒരിടത്ത്!" | screen (/) · cards (the Pooram, both calendars) · cta |
| general `streaks` | "നിങ്ങളുടെ സ്ട്രീക്ക് എത്ര?" (mid) | cards (awards) · logos (four daily) · cta |
| general `weekend-challenge` | "വീക്കെൻഡ് ചലഞ്ച്!" (mid) · tag "4 കളി, 1 ദിവസം" | logos (four daily) · steps (play all four, screenshot, comment) · cta |
| general `all-games` | "11 കളികൾ" · mid "മലയാളത്തിൽ!" | logos (all) · cards, not numbered (free, no ads, no login, Malayalam and English, phone and computer) · cta |

A general item has `"game": null` in the spec.

### Reel voice-over

- One `say` per beat: **Malayalam script only**, 2-8 words. Transliterate names and film titles
  (Kumbalangi Nights → കുമ്പളങ്ങി നൈറ്റ്സ്, Mohanlal → മോഹൻലാൽ). Spell numbers as Malayalam words
  or leave them out. Latin letters and digits come out garbled (the renderer warns).
- The first beat speaks the hook's first line, at once. Short lines with a full stop or question mark sound
  most natural ("നാല് സൂചന." "ഒരൊറ്റ സിനിമ.").
- On-screen text can be shorter than the voice line, but must say the same thing.
- The voice alternates by week on its own; leave `voice` null. Set `"date"` to the item's date. Don't
  change the speed in `voice.py`.
- The last scene's last beat: "പ്ലേ കേരളം ഡോട്ട് കോമിൽ സൗജന്യമായി കളിക്കൂ!".

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
