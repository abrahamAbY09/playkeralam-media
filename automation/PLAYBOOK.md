# Play Keralam Instagram: the weekly run

Every Sunday at 9:45 India time a fresh Claude session runs this playbook. It makes and schedules the
coming week's four Instagram posts for **@playkeralam**, fully automatically: no drafts, no approval.
Abr (the owner) only gets the summary at the end. Work through the steps in order. If a step fails, fix it
and carry on; if one post can't be made, schedule the others and say which failed and why.

Times are India time (Asia/Calcutta). "Today" is the Sunday the run starts.

## The rules that never bend

- **The brand is Play Keralam (പ്ലേ കേരളം), the site is playkeralam.com, the handle is @playkeralam.**
  Never write "Keralam Times", "keralamtimes" or any pages.dev address, in images, captions or speech.
- **No spoilers.** Daily games (Vaakku, Paryayam, Thaaranira, Katha) may only show **yesterday's** puzzle
  relative to the day the post goes out. `gamedata.js` only ever gives that one. Never work out, show or
  hint at today's or a future answer.
- **Only true facts.** Everything about a game comes from `games.json` or `facts.json` (made from the
  games' own data). Don't invent features, numbers, scores or quotes.
- **Malayalam first**, natural and warm, the way people in Kerala talk online. A short English line follows.
  Write proper Malayalam Unicode (atomic chillus such as ൻ ർ ൽ ൾ ൺ).
- **5 hashtags at most** (an Instagram limit), always including #PlayKeralam.
- **Four posts a week**: Monday post, Wednesday reel, Friday post, Saturday post, each at 9:00 pm.
  The Metricool free plan allows 20 posts a month; `plan_week.py` checks that.
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
4. Work in `automation/work/<monday-date>/` (git-ignored). Write scratch files there.

## 2. Plan the week

```
python3 automation/scripts/plan_week.py plan --run-date <today> > automation/work/<monday>/plan.json
```

- Exit code 3 / `"skip"`: this week is already scheduled. Stop and report that; do nothing else.
- Also call Metricool `getScheduledPosts` (brandId `7540170`, Monday 00:00 to Sunday 23:59, timezone
  Asia/Calcutta). If a post is already at 9 pm on a planned day, don't schedule a second one that day.
- If `overLimit` is not empty, drop general slots (Saturday first) until each month is within 20.

Each plan item has `date`, `kind` (post or reel), `topic` (a game id from `games.json`, or
`general:<name>`), `format` and `folder`.

## 3. Make each item

For each item, in its own folder `automation/work/<monday>/<folder>/`:

1. **Facts**: `node automation/scripts/gamedata.js --site <site> --date <item.date> --out facts.json`.
2. **Screenshot** (when the recipe uses one and the game has a `shot` path in games.json):
   `python3 automation/scripts/shoot.py --site <site> --date <item.date> --page <shot path> --out shot.png`
   (the front page is `--page /`). It shows the day before the post, in Malayalam, with the help box closed.
3. **Spec**: write `spec.json` following the recipe for the format (below) and the slide/scene types
   documented at the top of `render_post.py` / `render_reel.py`.
4. **Render**:
   - post: `python3 automation/scripts/render_post.py spec.json out`
   - reel: `python3 automation/scripts/render_reel.py spec.json out` (about 2 minutes)
5. **Look at it.** Read `out/contact-sheet.jpg` (and for a post every `out/slide-N.jpg`) as images.
   Check: the Malayalam reads correctly with no broken letters, nothing overlaps or is cut off, the
   facts match facts.json, no spoiler, the brand is right. A renderer `WARNING` that text "still overflows" or
   content is "taller than the slide" must be fixed (shorter text, fewer items); "shrank a lot" is fine if it
   still reads well on a phone. Re-render until it is clean.
6. **Caption**: write `out/caption.txt` (see *Captions*) and, for a post, `out/alt.json` (a list with one
   plain English alt text per slide).
7. **Check**: `python3 automation/scripts/check.py out` must pass.

### Recipes (posts: 4-6 slides; reels: 5-7 scenes, 25-35 seconds)

Puzzle formats show the puzzle, then the answer on the next slide or scene, then how the game plays and
the call to play. Use the facts exactly. `#N` is the puzzle number from facts (yesterday's).

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

A general item has `"game": null` in the spec. A reel item uses the same recipe as its format, as scenes.

### Reel voice-over

- Every scene has a `say` line: **Malayalam script only**. Transliterate names and film titles
  (Kumbalangi Nights → കുമ്പളങ്ങി നൈറ്റ്സ്, Mohanlal → മോഹൻലാൽ). Spell numbers as Malayalam words
  or leave them out. Latin letters and digits come out garbled.
- Keep each line short (8-16 words). The whole reel: about 60-80 words, 25-35 seconds.
- The voice alternates by week on its own; don't set `voice`. Set `"date"` to the item's date.
- The last scene's `say` invites people: "പ്ലേ കേരളം ഡോട്ട് കോമിൽ സൗജന്യമായി കളിക്കൂ. ലിങ്ക് ബയോയിൽ ഉണ്ട്."

### Captions

```
<Malayalam hook, one line>

<1-2 Malayalam lines: what's in the post, or the puzzle question>

<English, 1-2 short lines saying the same>
<A question to comment on> and <a "send this to ..." line>

ലിങ്ക് ബയോയിൽ · Link in bio · playkeralam.com

#PlayKeralam #... (5 in all, from config.json captions.tagPool, matched to the topic)
```

Puzzle posts must not give the answer in the caption. Keep it under about 900 characters.

## 4. Publish the media

1. Copy the finished files into the repo at `<folder>/`: a post's `slide-N.jpg`, or a reel's `reel.mp4`
   and `cover.jpg`. Don't commit `automation/work/`.
2. Commit ("Week of <monday>: media for 4 posts") and push to `main`.
3. Check every file's public link answers 200 with the right size:
   `https://raw.githubusercontent.com/abrahamAbY09/playkeralam-media/main/<folder>/<file>`
   (curl it from the shell; give it a minute after the push if the first try is 404).

## 5. Schedule in Metricool

For each item call `createScheduledPost` with `blogId` `"7540170"` and `date` `"<item.date>T21:00:00+05:30"`.
`info` is a JSON string:

Post:
```json
{"autoPublish": true, "draft": false, "text": "<caption.txt>",
 "media": ["<raw link to slide-1.jpg>", "..."], "mediaAltText": ["<alt 1>", "..."],
 "providers": [{"network": "instagram"}],
 "publicationDate": {"dateTime": "<item.date>T21:00:00", "timezone": "Asia/Calcutta"},
 "instagramData": {"type": "POST", "isAiGenerated": true},
 "shortener": false, "smartLinkData": {"ids": []}, "descendants": [], "firstCommentText": "", "hasNotReadNotes": false}
```

Reel: the same, with `"media": ["<raw link to reel.mp4>"]`, no `mediaAltText`,
`"videoCoverMilliseconds": <coverMs from out/reel.json>` and
`"instagramData": {"type": "REEL", "showReelOnFeed": true, "isAiGenerated": true}`.

Keep each result's `uuid` and `plannerUrl`. If a call fails, read the error, fix what it says (wrong
format, too many hashtags, a link not yet live) and try once more; if it fails again, skip that item.

## 6. Record and report

1. Write `results.json`: `[{"slot": <n>, "date": "...", "metricoolUuid": "...", "plannerUrl": "...", "folder": "...", "title": "<short description>"}]`
   for each scheduled item, then
   `python3 automation/scripts/plan_week.py record --plan plan.json --results results.json`.
2. Commit `automation/rotation.json` ("Rotation after week of <monday>") and push.
3. Call `getScheduledPosts` for the week and confirm the four posts are there, `autoPublish` true and not drafts.
4. Finish with a short summary for Abr: each day, what goes out (topic, format, the caption's first line),
   its planner link, and anything that failed or looked off. No other questions; nothing needs his OK.
