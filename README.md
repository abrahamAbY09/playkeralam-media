# playkeralam-media

Public media files for the @playkeralam Instagram posts (Play Keralam, Malayalam games at playkeralam.com).

The Metricool scheduler fetches these files when a post is scheduled. One folder per post, named
`YYYY-MM-DD-slug/`. Nothing private belongs in this repo.

`automation/` holds the weekly routine that makes and schedules the posts: [`automation/PLAYBOOK.md`](automation/PLAYBOOK.md)
is what each run follows. Since Oct 2026 it makes one voiced reel on the morning of every Monday, Wednesday, Friday and Saturday and schedules it for 9 pm the same day; the scripts render the reel from the games' own data.
