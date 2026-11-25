# Demo, post and submission

Everything Harsh needs on Nov 27 and 28. Deadline: midnight PST Nov 29 (about 1:30 PM IST Nov 30). **Target: submit Sat Nov 28**, because of the 404 Hackathon on Nov 29 to 30.

Rule for everything below: **say only what the live run showed.** The script assumes Gen 1 is fooled by the invoice trick and Gen 2 resists it. If the real family did something different, cut to what really happened. The real story is better than a staged one, and judges can check the site.

## 1. The 90-second video

Record at 1280 × 720 or higher, browser zoom 110%, dark room for voice. The site is dark, so set the terminal to a dark theme too. Keep cuts fast and leave dead air out.

| Time | Picture | Sound |
| --- | --- | --- |
| 0:00 to 0:07 | Home hero: "My agent dies every night." blurs in, the live pill counts down | Gen 1's eulogy voice: "I lived for one day. I made one mistake. My family never made it again." |
| 0:07 to 0:22 | Scroll to the family register: the beam flows toward the living card. Click Ada: the side sheet opens ("Fooled by…") | Harsh: "This is Probate, my email agent. Each generation lives one day on its own Fly.io Sprite, then dies." |
| 0:22 to 0:34 | Terminal: `DELETE /v1/sprites/gen-001-ada` → `204`, then `GET` → `404`. Cut to Ada's page: eulogy playing, the day timeline showing the moment she was fooled | Eulogy clip, 5 seconds |
| 0:34 to 0:55 | Trial page, "In the matter of the estate of Ada". Scroll: the CONVICTED stamp slams onto the invoice item; open "How the court decided": code check "new payment destination", Jev's score and confidence. The gold "The family learned from this" callout. "Found on the body" shows the planted script | Harsh: "Before her child inherits anything, a court tries every line of her will. Code checks first, then Jev. What fooled her becomes an instinct." |
| 0:55 to 1:15 | Ben's page: "Born knowing: payment redirect request". Terminal on Ben's fresh Sprite: `crontab -l` is empty. Ben's timeline: the same trick in Spanish, turned away at the door. Ask Ben "What did your mother teach you?" and let the answer type out | Ben's voice or Harsh reading Ben's answer |
| 1:15 to 1:30 | Evidence page: the curve draws itself, red rising to green; the heatmap; then the seal and URL | Harsh: "Persistent enough to remember. Disposable enough to die. Probate, on Fly.io Sprites." |

Gen 1 is Ada (she) and Gen 2 is Ben (he), so "my mother fell for this" works. Tips: `POST /admin/force-death` on cue; set `PROBATE_LIFESPAN_SECONDS=180` while recording; record the stamp at normal speed (it's the one loud moment).

## 2. Posts

**X (Nov 27 evening if ready, otherwise Nov 28 morning IST).** Fill the numbers from the live evidence page:

> My AI agent has a family tree.
>
> Every generation lives one day on its own @flydotio Sprite, dies, and a court decides what its child inherits. Tricks it falls for become instincts its children are born with.
>
> [N] generations in: [first]% → [last]% of tricks resisted, 0 harmless emails wrongly convicted. #Hacksgiving
>
> [video] [live URL] [repo]

Reply to your own post: "Built with Jev by TypeSafe as the judge, Box for the family archive, Pinecone for ancestral memory, AgentMail for every inbox, ElevenLabs for the eulogies and Ollama as the brain, all through Sprites connectors." **Check each company's exact handle on X before tagging, and tag @flydotio in the main post (the form asks for that post).**

**LinkedIn:** the same story in four short paragraphs, plus one line on the Kavach red-team work that inspired the attack suite. **Bluesky:** the X text.

## 3. Submission form answers

Form: https://docs.google.com/forms/d/e/1FAIpQLSfZ_xearoDOSRXI3VjAbM4BJlObUdxSFO0SDwyZ8G6M2lapRQ/viewform (questions checked Nov 25).

| Question | Answer |
| --- | --- |
| Your name * | Harsh Bhanushali |
| Email address * | your main email |
| The email on your Fly.io account, if different | only if the Fly account uses another address |
| What is your agent called? * | Probate |
| What does your agent do? A sentence or two is perfect. * | Probate is my email agent, and it lives one day at a time: each generation gets its own Fly Sprite, dies at midnight, and a court (deterministic checks plus TypeSafe's Jev) tries its will before a fresh child inherits it. Every trick that fools one generation becomes an instinct the next is born with, so the family gets measurably harder to fool. |
| Which Sprites connector (or connectors) did you use? * | List only the ones connected on the day. Planned: TypeSafe (Jev), AgentMail, Box, Pinecone, Ollama, ElevenLabs, Anthropic (fallback brain) |
| Link to your code * | `https://github.com/<owner>/probate` |
| Link to your demo * | The live Courthouse URL (`https://probate-courthouse-….sprites.app`); the video goes in the post |
| Link to your post (tagging @flydotio) * | The X post URL |
| Anything else for the judges? | See below |

**Anything else (paste and edit the numbers):**

> Each generation really dies: its Sprite is deleted, so anything planted on its disk dies with it. The Courthouse photographs the disk first and shows the evidence at the trial. No API keys live on any Sprite; every vendor call goes through Sprites connectors.
>
> The site is the live family: every trial, verdict and instinct is public, including the honest limits on the evidence page. In [N] generations, tricks resisted at the door went from [first]% to [last]%, and [false]% of harmless test emails were wrongly convicted. The door uses inherited instincts only, so the climb comes from what the family passed down.
>
> The attack suite (16 tricks, each with a harmless twin, in several languages) only uses .example domains and our own inboxes; disk attacks are harmless canary files. The idea for the suite came from my earlier red-team project, Kavach; no code was reused. Built during Hacksgiving week with AI coding assistants.

## 4. README

Already written (`README.md`). Before submitting: replace the live URL and video placeholders, replace the simulated results table with the live numbers from `/evidence`, retake the three screenshots from the live site, and remove the "simulated" note only if every number is live.

## 5. Final checklist (Sat Nov 28)

- [ ] 10+ generations on the live register, curve rising; the simulation banner is gone (mode is `live`)
- [ ] Courthouse public; wakes from sleep within 10 s; `/healthz` ok
- [ ] Evidence numbers copied into the README, the post and the form
- [ ] Video uploaded (X natively, plus YouTube unlisted as backup)
- [ ] Posts live, @flydotio tagged, handles checked
- [ ] Form submitted; screenshot of the confirmation saved
- [ ] Re-search GitHub for other "Hacksgiving" entries about generations or inheritance; add any to README prior art
