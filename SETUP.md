# Setup

This repo is a GitHub **profile README** (`Pawani0/Pawani0`) plus a self-updating
animated **T-Rex contribution game**.

## 1. File layout
```
Pawani0/                 # repo named exactly like your username
├─ README.md             # your profile (rendered on github.com/Pawani0)
├─ scripts/
│  ├─ generate_trex.py   # builds the animated T-Rex SVG
│  └─ fetch_contributions.py
├─ .github/workflows/
│  └─ contribution-games.yml
└─ assets/
   └─ dino-game.svg      # local demo preview (the Action overwrites the live one)
```

## 2. Fill in the placeholders
In `README.md`, replace:
- `https://www.linkedin.com/in/REPLACE_ME` → your LinkedIn URL
- `REPLACE_ME@example.com` → your email

## 3. Push to the `Pawani0/Pawani0` repo, then run the workflow once
- Go to the **Actions** tab → **Generate contribution games** → **Run workflow**.
- It fetches your live contributions, builds the T-Rex SVG + snake, and pushes
  them to a branch called `output`.
- The README links to `…/output/dino-game.svg`, so those images **404 until the
  first run finishes** — that's expected.

The workflow then re-runs automatically twice a day, so the game always reflects
your latest graph. The default `GITHUB_TOKEN` is enough for public contributions;
if your graph is private, add a Personal Access Token as a secret and swap it in.

## 4. Preview / tweak locally
```bash
# synthetic data preview, no token needed
python scripts/generate_trex.py --demo --output assets/dino-game.svg

# from real data
GH_TOKEN=<token> GH_LOGIN=Pawani0 python scripts/fetch_contributions.py contributions.json
python scripts/generate_trex.py --input contributions.json --output assets/dino-game.svg
```
Tunable constants live at the top of `generate_trex.py` (`JUMP_H`, `RUN_SECONDS`,
`LEVEL_COLORS`, obstacle threshold, etc.).

## Note on "interactive"
GitHub strips JavaScript from rendered markdown, so nothing in a README can be
*played* — the snake/arcade graphs everyone uses are auto-playing **animations**,
and so is this T-Rex. If you want a genuinely playable version, host the game on
**GitHub Pages** (a normal HTML/JS page) and link to it from the README; that runs
JS freely. The README embed will always be the animated SVG.
