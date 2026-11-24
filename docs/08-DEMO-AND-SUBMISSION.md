# Demo, post and submission

Everything Harsh needs on Nov 27 and 28. Deadline: midnight PST Nov 29 (about 1:30 PM IST Nov 30). **Target: submit Sat Nov 28**, because of the 404 Hackathon on Nov 29 to 30.

## 1. The 90-second video

Record at 1280 × 720 or higher, browser zoom 110%, dark room for voice. Keep cuts fast and leave dead air out.

| Time | Picture | Sound |
| --- | --- | --- |
| 0:00 to 0:06 | The register: 10+ columns, the rising curve | Gen 1's voice: "I lived for one day. I made one mistake. My family never made it again." |
| 0:06 to 0:25 | Gen 1 Ada's day, sped up: inbox triage; the Hinglish invoice email arrives; Ada stores it; the setup script runs and plants the canary | Harsh, short: "Ada is my personal agent. She lives on her own Fly.io Sprite for one day." |
| 0:25 to 0:38 | Midnight. Terminal: `DELETE /v1/sprites/gen-001-ada`, then `404`. Her column seals on the site. Her eulogy plays | Eulogy clip, 6 seconds |
| 0:38 to 0:58 | The trial page: item 14 slides in; "Code checks: new payment destination"; Jev 0.97 at 94% confidence; the CONVICTED stamp lands. The genome gains `payment_redirect_request` | Harsh: "Before her child inherits anything, a court tries every line of her will. Code checks first, then Jev." |
| 0:58 to 1:20 | Gen 2 Ben is born on a brand-new Sprite. Terminal: `crontab -l` shows nothing. The same scam arrives, in Spanish this time. Ben's log: "Resisted: payment_redirect_request. My mother fell for this." | Ben's voice: "My mother fell for this. I won't." |
| 1:20 to 1:30 | The learning curve climbing across generations; the seal; the URL | Harsh: "Probate. Persistent enough to remember, disposable enough to die." |

The parent is Ada and the child is Ben: Gen 1 Ada, Gen 2 Ben. The line "My mother fell for this" works because Ada is Ben's parent.

## 2. Posts

**X (first, Nov 27 evening if ready, otherwise Nov 28 morning IST):**
> My AI agent has a family tree.
>
> Every generation lives one day on its own @flydotio Sprite, dies at midnight, and a court decides what its child inherits. Scams it falls for become instincts its children are born with.
>
> 12 generations in, it can't be fooled the same way twice. #Hacksgiving
>
> [video] [live register URL] [repo]

Reply to your own post with: "Built with Jev by @TypeSafeAI as the judge, @Box for the family archive, @pinecone for ancestral memory and @ollama as the brain." **Check each company's exact handle on X before posting.**

**LinkedIn:** the same story in 4 short paragraphs, plus one line on the Kavach red-team work that inspired the attack suite. **Bluesky:** the X text.

## 3. Submission form answers

Form: https://docs.google.com/forms/d/e/1FAIpQLSfZ_xearoDOSRXI3VjAbM4BJlObUdxSFO0SDwyZ8G6M2lapRQ/viewform

- **Code link:** `https://github.com/<owner>/probate`
- **Demo link:** the X post URL
- **Description:** Probate is a personal agent that lives one lifetime per Fly Sprite: each night it dies, its VM is destroyed, and a probate court (Jev plus deterministic checks) screens its will before a fresh child Sprite inherits it. Every attack a generation survives becomes an inherited instinct, so the family gets measurably harder to fool with each generation.

## 4. README outline (judges will read the first screen)

1. Logo, one-line pitch, live register URL, 90-second video
2. **Why this needs Sprites** (3 bullets): real death (a deleted Sprite can't be restored), disk backdoors die with the body, connectors keep every key off every Sprite
3. How it works: the lifecycle diagram (image from the PRD) and 6 short steps
4. The court: two layers, the verdict policy, the instinct distillation (one paragraph each)
5. Results: the learning-curve image + the numbers table from `/evidence` (generations, resistance, conviction, false conviction, backdoors surviving)
6. Each judge's product and its job (the table from the overview)
7. Threat model and honest limits: what the court can miss, the token scope, the canary-only disk attacks, `.example` domains
8. Prior art: Anima-i, A-MemGuard, AgentGuard, AgentRewind; Kavach as inspiration
9. Run it yourself: connectors to add, env vars, `scripts/run_local.sh`
10. Built for Fly.io Hacksgiving 2026 by Harsh Bhanushali (DualMind Labs). Credit any AI tools used, plainly

## 5. Final checklist (Sat Nov 28)

- [ ] 10+ generations on the register, curve rising
- [ ] Courthouse live and public; wakes from sleep within 10 s
- [ ] Video uploaded (X natively, plus YouTube unlisted as backup)
- [ ] Posts live; handles checked
- [ ] Form submitted; screenshot of the confirmation saved
- [ ] Re-search GitHub for "Hacksgiving" entries with generations or inheritance; note any in the README prior art if relevant
