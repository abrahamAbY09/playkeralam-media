# ElevenLabs voice for the story reels

Status (24 Nov 2026): **wired and working.** `config.json` → `voice.provider` is `"eleven"`, the cast's voices are set,
`voice_lines.py` handles the budget, the cache and the download, and the first line (the sign-off) is in the cache.

Two settings outside this repo make it work; if a run says either is missing, this is where they live:

1. **Network:** claude.ai **Settings > Capabilities > Allowed websites** lists `elevenlabsusercontent.com` (added
   24 Nov 2026, with "Standard download sites only" kept). That is where the connector puts the audio files; without
   it the workspace proxy refuses the download (HTTP 403). `python3 automation/scripts/voice_lines.py preflight` checks
   it for free. (The Claude Code cloud-environment setting does not apply to these Play Keralam project sessions.)
2. **Connector:** the run needs the ElevenLabs connector's tools (`mcp__ElevenLabs__*`). If a run doesn't have them it
   falls back to Piper and sends a push notification.

## What the connector test showed (24 Nov 2026)

- Abr's account: free plan, 10,000 credits a month, resetting on the 24th (next: 24 Dec 2026, 23:07 India time).
- Library voices work on the free plan through the connector without using any of the 3 voice slots.
- `eleven_v3` with Malayalam text: 1 credit per character, counting spaces, punctuation and any `[tag]`. Python's
  `len()` of the prompt matches the charge exactly (the 38-character sign-off cost 38 credits). Duration: about
  19 characters a second.
- `creative_generate_speech` has no language parameter; v3 reads the language from the Malayalam script.
- The audio lives at a signed `https://elevenlabsusercontent.com/...content.mp3` URL (mp3, 44.1 kHz mono, ~192 kbps)
  that expires after a few hours. `creative_get_generations` gives a fresh one for any old generation, for free.
- Do NOT use `creative_execute_sandbox` to move audio: it has no network, returns only ~10 KB of output per call and
  costs about 2 credits a second.
- The test line was the fixed sign-off ("പ്ലേ കേരളം ഡോട്ട് കോമിൽ കളിച്ചുനോക്കൂ.", narrator), so it isn't wasted:
  it was downloaded once the network setting was added and is in `voice-cache/eleven/` (2.0 s); every reel reuses it
  free.

## Why the care

1 credit per character and about 20 reels a month leaves roughly 450-500 characters per reel with nothing to spare.
The free plan also requires crediting ElevenLabs (the caption line in `voice.eleven.attribution`) and does not allow
commercial use; on a paid plan set `attribution` to "" and raise `monthlyCredits`.

## Rules

- One generation per line, ever (`generations_count` 1; the connector's default is 2, which doubles the cost).
- No auditions, no test lines, no "one more take", no `estimate_only` loops. Voices are picked from the free listing.
- A line is logged as paid the moment `fetch` starts, so a failed download is fetched again later, never re-voiced.
- Push the cache and `voice-usage.json` straight after voicing, before rendering.
- If the tools are missing, preflight fails, credits are short or a generation fails, stop using ElevenLabs for that
  reel: render with `"voiceProvider": "piper"` and say so in the summary (plus a push notification when the tools are
  missing or preflight fails, so Abr can fix the setting).

## Connector steps (every story reel, after the script is frozen)

1. Load the tools in one ToolSearch call:
   `select:mcp__ElevenLabs__account_get_usage,mcp__ElevenLabs__creative_create_flow,mcp__ElevenLabs__creative_generate_speech,mcp__ElevenLabs__creative_get_flow_run_status,mcp__ElevenLabs__creative_get_generations`.
   Nothing found: Piper.
2. `python3 automation/scripts/voice_lines.py preflight`. Not exit 0: Piper.
3. `account_get_usage` → LEFT = `character_limit` − `character_count`.
4. `python3 automation/scripts/voice_lines.py plan <folder>/spec.json --left LEFT`. Exit 2: shorten lines (or drop
   tone tags) and plan again. Exit 3: Piper. The last line of output is JSON with `voice` (lines to generate) and
   `fetch` (lines already paid).
5. `creative_create_flow` with name `Play Keralam reel <date>` → FLOW.
6. For each entry in `voice`, exactly one call:
   `creative_generate_speech` {`prompt`: the entry's `prompt` exactly, `model_id`: "eleven_v3", `voice_id`: the
   entry's `voiceId`, `generations_count`: 1, `flow_id`: FLOW}. Keep the returned `session_ids` and the
   `pending[0].generation_id` against the line's `n`. Never call it again for the same line, even if it errors.
7. `creative_get_flow_run_status` {`flow_id`: FLOW, `session_ids`: all of them}; wait `poll_after_seconds` between
   calls until `all_completed` or `has_failures`. For each completed generation take its `media[].url` (same as
   `generations[].content_url`) and run
   `python3 automation/scripts/voice_lines.py fetch <folder>/spec.json N "URL" --flow FLOW --gen GENERATION_ID`.
   A failed generation: don't retry it; render the reel with Piper and report it.
8. For each entry in `fetch` (paid by an earlier run): `creative_get_generations` {`flow_id`: its `flow`,
   `generation_ids`: [its `gen`]} → `full_res_url` → `voice_lines.py fetch ... N "URL" --flow ... --gen ...`.
9. `git add automation/voice-cache automation/voice-usage.json`, commit, push. Then render (the renderer reads only
   the cache; a line missing from it stops the render instead of spending credits).
10. The caption carries `voice.eleven.attribution`; the summary gives the credits this reel used and LEFT after it.

## Cast voices (picked 24 Nov 2026 from the library listing, no auditions)

| Character | Voice | Voice id |
| --- | --- | --- |
| Ammachi | Solly Rajan Philips (older Malayali woman) | `n4fEDQwxuAjplyp0aJy4` |
| Kuttan uncle | Aby (middle-aged man, south Kollam Malayalam) | `jC5gBeWiOWA75lYTC3ux` |
| Appu | Ajay - Engaging Malayalam tone (young man, made for reels) | `yK5OyHRDkLof80lsqkUP` |
| Meenu | Namitha - Young Malayalam Voice (young woman, bright, conversational) | `YC7kIECPG5vM2RiP22Rd` |
| Narrator | same as Appu (so the sign-off line is shared) | `yK5OyHRDkLof80lsqkUP` |

To change a voice, change its id in `config.json` → `voice.eleven.cast` only after Abr asks; every cached line of
that character then counts as new and is paid again when next used.
