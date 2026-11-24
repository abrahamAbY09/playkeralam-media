# ElevenLabs voice for the story reels

Status (24 Nov 2026): **not wired yet.** `config.json` → `voice.provider` stays `"piper"` until a chat session has
connected the ElevenLabs connector, voiced one short test line, confirmed the audio reaches the workspace, picked the
cast's voices and written the exact steps below. Until then the daily run uses Piper. Do not call ElevenLabs from a
scheduled run while `voice.provider` is `"piper"`: an attempt whose audio can't be saved still costs credits.

## Why the care

Abr is on ElevenLabs' free plan: 10,000 credits a month, 1 credit per character of text (spaces and punctuation
count). At about 20 reels a month that is roughly 450-500 characters per reel with nothing to spare. The free plan
also requires crediting ElevenLabs (the caption line in `voice.eleven.attribution`) and does not allow commercial use;
on a paid plan set `attribution` to "" and raise `monthlyCredits`.

## Rules

- One generation per line, ever. `voice_lines.py plan` shows which lines still need voicing; everything else comes
  from `automation/voice-cache/eleven/` for free.
- No auditions, no test lines, no "one more take". Pick voices from the library listing (free), not by generating.
- Push the cache and `voice-usage.json` straight after voicing.
- If the connector is missing in a run, or a generation fails, stop using ElevenLabs for that reel: render with
  `"voiceProvider": "piper"` and say so in the summary (and in a push notification if the connector is missing).

## Connector steps

(To be filled in after the first test: the tool name, its arguments for model `eleven_v3`, language `ml` and a voice
id, and how its audio lands in the workspace so `voice_lines.py put` can store it.)

## Cast voices

(To be filled in: one voice id per character in `config.json` → `voice.eleven.cast`.)
