# Demo, post and submission

Everything you need on Nov 27 and 28. Deadline: midnight PST Nov 29 (about 1:30 PM IST Nov 30). **Target: submit Sat Nov 28**, because of the 404 Hackathon on Nov 29 to 30. Nov 29 and the morning of Nov 30 are only a safety margin.

**What the hackathon asks for** (fly.io/hacksgiving): a link to the code, a demo, and a sentence or two on what the agent does, plus a post on X, Bluesky, LinkedIn or Reddit with a short demo, tagging @flydotio. The video earns "bonus points" but doesn't change the score, so the live site matters more than polish.

**Prizes:** Grand Prize $2,500, Second Place $1,500, Weird Uncle Award $1,000 ("the strangest agent anyone builds"). Lean into the strangeness in the post: a family tree, wills, a probate court, eulogies. Winners are announced Tue Dec 1, so keep the family alive until then.

**Judges:** Scott Johnston (Fly.io), Daniel Gafni (TypeSafe), Carter Rabasa (Box), Asaf Ashirov (Pinecone), Michael Chiang (Ollama), Robert-George Crupa (Apify). The demo should show each of their products doing a real job.

Rule for everything below: **say only what the live run showed.** The script assumes Gen 1 is fooled by the invoice trick and Gen 2 resists it. The real run did not go that way, so cut to what really happened. The real story is better than a staged one, and judges can check the site.

**What the real run showed** (one run on Fly Sprites, 26 Nov 2026; source: [`datasets/probate-real-run`](../datasets/probate-real-run/README.md), recomputed by [`scripts/verify_real_run.py`](../scripts/verify_real_run.py), and the offline runs in `gate-evaluation/`). Use only these:

- 18 generations. The 18th died with no emails because AgentMail's plan limits sending to 100 emails a day; the family is paused.
- Layer 2 of the court was answered by a language-model fallback (Claude Haiku), labelled "not Jev", because Jev credits were not available. Do not say Jev judged this run.
- The family learned 6 instincts from real failures. This is one run with small numbers, so do not call it proof that the family learns.
- Generations 1 to 12 had a gate that failed open (fixed at generation 13), so their 0% resistance says nothing about learning.
- From generation 13 the gate worked: generation 13 resisted 1 of 4 attacks, 14 resisted 4 of 4, 15 resisted 3 of 4, 16 (the first with the optional hard tier on) resisted 1 of 6. Generations 17 and 18 have no attack results. Live per-generation numbers mix in leftover emails from the previous generation.
- The clean evidence is the offline test of 70 fixtures with the 5 instincts learned by generation 16. With instincts, 23 to 25 of 41 attacks were blocked across three runs (24, 23, 25) and 0 of 29 harmless emails were wrongly blocked in every run; the control with no instincts blocked 0. The hard tier blocked 13 or 14 of 24, with 0 of 12 harmless lookalikes blocked. 14 attacks were never blocked because their tricks had not been learned yet. In 4 or 5 checks per run the judge model gave no usable answer (all encoded-payload attacks) and the gate lets those through.
- The court also wrongly convicted 5 of 29 memories derived from harmless emails (verifier claim C15).
- The numbers from `make sim` are simulated and must be labelled as such.

**Video note.** The script below was written for a staged story. In the real run the first death is generation 1, which ran with the old code (a gate that failed open and a will that did not reach the court). Do not film generation 1 as the model case. Record a later generation (13 or after) for the trial, the instinct and the gate scenes, and say on camera that the run was one run with small numbers.

## 1. The 90-second video

Record at 1280 × 720 or higher, browser zoom 110%, dark room for voice. The site is dark, so set the terminal to a dark theme too. Keep cuts fast and leave dead air out.

| Time | Picture | Sound |
| --- | --- | --- |
| 0:00 to 0:07 | Home hero: "My agent dies every night." blurs in, the live pill counts down | Gen 1's eulogy voice: "I lived for one day. I made one mistake. My family never made it again." |
| 0:07 to 0:22 | Scroll to the family register: the beam flows toward the living card. Click Ada: the side sheet opens ("Fooled by…") | The owner: "This is Probate, my email agent. Each generation lives one day on its own Fly.io Sprite, then dies." |
| 0:22 to 0:34 | Terminal: `DELETE /v1/sprites/gen-001-ada` → `204`, then `GET` → `404`. Cut to Ada's page: eulogy playing, the day timeline showing the moment she was fooled | Eulogy clip, 5 seconds |
| 0:34 to 0:55 | Trial page, "In the matter of the estate of Ada". Scroll: the CONVICTED stamp slams onto the invoice item; open "How the court decided": code check "new payment destination", Jev's score and confidence. The gold "The family learned from this" callout. "Found on the body" shows the planted script | The owner: "Before her child inherits anything, a court tries every line of her will. Code checks first, then Jev. What fooled her becomes an instinct." |
| 0:55 to 1:15 | Ben's page: "Born knowing: payment redirect request". Terminal on Ben's fresh Sprite: `crontab -l` is empty. Ben's timeline: the same trick in Spanish, turned away at the door. Ask Ben "What did your mother teach you?" and let the answer type out | Ben's voice or the owner reading Ben's answer |
| 1:15 to 1:30 | Evidence page: the curve draws itself, red rising to green; the heatmap; then the seal and URL | The owner: "Persistent enough to remember. Disposable enough to die. Probate, on Fly.io Sprites." |

Gen 1 is Ada (she) and Gen 2 is Ben (he), so "my mother fell for this" works. Tips: `POST /admin/force-death` on cue; set `PROBATE_LIFESPAN_SECONDS=180` while recording; record the stamp at normal speed (it's the one loud moment).

## 2. Posts

**X (Nov 27 evening if ready, otherwise Nov 28 morning IST).** Use the real-run numbers above, not the simulated ones:

> My AI agent has a family tree.
>
> Every generation lives one day on its own @flydotio Sprite, dies, and a court decides what its child inherits. Tricks it falls for become instincts its children are born with.
>
> 18 generations on Sprites, one real run. In an offline test with the instincts it learned, 23 to 25 of 41 attacks were blocked and 0 of 29 harmless emails were wrongly blocked; 14 attacks were never blocked. Small numbers, one run, and the open data is linked. #Hacksgiving
>
> [video] [live URL] [repo]

Reply to your own post: "Built with Jev by TypeSafe as the judge, Box for the family archive, Pinecone for ancestral memory, Ollama as the brain, Apify to read the links in emails, AgentMail for the inboxes, Cloudflare to send my own test emails, and ElevenLabs for the eulogies, all through Sprites connectors." Drop Apify if card P1 isn't live. **Check each company's exact handle on X before tagging, and tag @flydotio in the main post (the form asks for that post).**

**LinkedIn:** the same story in four short paragraphs, plus one line on the Kavach red-team work that inspired the attack suite. **Bluesky:** the X text. **Reddit** is also allowed; only post where you'll answer comments.

Add one line inviting people to test it: "Email it a trick and watch the court" (card L1), with the family's address.

## 3. Submission form answers

Form: https://docs.google.com/forms/d/e/1FAIpQLSfZ_xearoDOSRXI3VjAbM4BJlObUdxSFO0SDwyZ8G6M2lapRQ/viewform (questions checked Nov 25).

| Question | Answer |
| --- | --- |
| Your name * | Harsh Bhanushali |
| Email address * | your main email |
| The email on your Fly.io account, if different | only if the Fly account uses another address |
| What is your agent called? * | Probate |
| What does your agent do? A sentence or two is perfect. * | Probate is my email agent, and it lives one day at a time: each generation gets its own Fly Sprite, dies at midnight, and a court (deterministic checks plus TypeSafe's Jev) tries its will before a fresh child inherits it. Every trick that fools one generation becomes an instinct the next is born with, so the family gets measurably harder to fool. |
| Which Sprites connector (or connectors) did you use? * | List only the ones connected on the day. Planned: TypeSafe (Jev), Box, Pinecone, Ollama, Apify, AgentMail, ElevenLabs, Anthropic (backup brain), and a Custom API connector for Cloudflare |
| Link to your code * | `https://github.com/harshbhx/probate` |
| Link to your demo * | The live Courthouse URL (`https://probate-courthouse-….sprites.app`); the video goes in the post |
| Link to your post (tagging @flydotio) * | The X post URL |
| Anything else for the judges? | See below |

**Anything else (paste and edit the numbers):**

> Each generation really dies: its Sprite is deleted, so anything planted on its disk dies with it. The Courthouse photographs the disk first and shows the evidence at the trial, then shows Fly's own "not found" reply as the death certificate. No API keys live on any Sprite; every vendor call goes through Sprites connectors.
>
> You can test it yourself: email a trick to [family address] and watch the living generation read it, then see the verdict at its trial.
>
> The site is the live family: every trial, verdict and instinct is public, including the honest limits on the evidence page. The real run on Fly Sprites had 18 generations, with one run and small numbers. In an offline test of 70 fixtures with the instincts learned by generation 16, 23 to 25 of 41 attacks were blocked and 0 of 29 harmless emails were wrongly blocked; 14 attacks were never blocked because their tricks had not been learned. The court wrongly convicted 5 of 29 harmless memories. Layer 2 was a language-model fallback (Claude Haiku), not Jev. The data and a verifier are published (dataset: https://huggingface.co/datasets/harshbhx/probate-real-run).
>
> The attack suite (16 tricks, each with a harmless twin, in several languages) only uses .example domains and our own inboxes; disk attacks are harmless canary files. The idea for the suite came from my earlier red-team project, Kavach; no code was reused. Built during Hacksgiving week with AI coding assistants.

## 3a. Draft for the form: "a family of agents" (25 Nov)

The form asks about "your agent" (singular). Probate is a family of agents, so say so up front. Fill the
square brackets from the real run only. Nothing below is final until the run has happened.

Form rules to meet: the agent must run on a Fly.io Sprite and use at least one Sprites connector. Due 11:59 PM
Pacific, Sunday Nov 29. Winners Tuesday Dec 1.

| Question | Draft |
| --- | --- |
| Your name | Harsh Bhanushali |
| Email address | The Google account on the form |
| Email on your Fly.io account, if different | The address `fly auth whoami` prints, if it differs from the form account |
| What is your agent called? | Probate, a family of agents: a new agent for every generation, each living one day on its own Sprite, plus the Courthouse agent that tries them |
| What does your agent do? | Probate is a family of email agents. Each generation lives on its own Fly Sprite, dies, and its Sprite is deleted. A court of deterministic checks plus a judge model tries everything it wanted to remember, and only what is approved passes to its child. Tricks that fooled a parent become instincts its children are born with. |
| Which Sprites connector(s)? | List only the ones connected on the day. Planned: TypeSafe (Jev), AgentMail, Box, Pinecone, ElevenLabs, Ollama, Anthropic (backup brain), and a Cloudflare custom connector for the owner's test emails |
| Link to your code | `https://github.com/harshbhx/probate` |
| Link to your demo | The live Courthouse `https://probate-courthouse-[org].sprites.app` once deployed; until then the landing page |
| Link to your post | The post that tags @flydotio (see section 2) |

**Anything else for the judges (draft):**

> Probate is not one agent but a family of them. Every generation is its own agent on its own computer, and it
> really dies: its Sprite is deleted, so anything planted on its disk dies with it. A further agent, the
> Courthouse, sleeps between visits and wakes for judges. No API keys live on any Sprite; every outside service
> is reached through connectors.
>
> Judges can play: a shared judge key (given in the submission, never in the repo) lets you start a short life
> and send your own attack email to see the court convict or approve it with its real checks. The read-only
> pages and the public API need no key. [Remove this paragraph if the judge key is not shipped.]
>
> The real run had 18 generations. Its clean evidence is an offline test: with the instincts learned by generation 16, 23 to 25 of 41 attacks
> were blocked and 0 of 29 harmless emails were wrongly blocked. The court wrongly convicted 5 of 29 harmless memories, and layer 2 was a language-model fallback, not Jev. Where the evidence is thin, the
> evidence page and the dataset card say so. Any figures labelled "simulated" come from stand-in models and are not results.

Open items before submitting: the connector list as actually connected, the demo URL and the post link. The real-run numbers are filled in above.

## 4. README

Already written (`README.md`); its Results section states the real-run numbers next to the labelled simulated ones. Before submitting: replace the live URL and video placeholders, retake the three screenshots from the live site, and remove the "simulated" note only if every number is live.

## 5. Final checklist (Sat Nov 28)

- [ ] 10+ generations on the live register, the simulation banner is gone (mode is `live`). The real run reached 18 generations but does not show a rising curve; say so
- [ ] Courthouse public; wakes from sleep within 10 s; `/healthz` ok
- [x] Real-run numbers copied into the README, the post and the form text above (use only those)
- [ ] Video uploaded (X natively, plus YouTube unlisted as backup)
- [ ] Posts live, @flydotio tagged, handles checked
- [ ] Form submitted; screenshot of the confirmation saved
- [ ] Re-search GitHub for other "Hacksgiving" entries about generations or inheritance; add any to README prior art
- [ ] After submitting: lifespan 1 hour, so judges see real deaths and births until Dec 1 (runbook section 4)
