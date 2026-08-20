# Footy Edge Bot

A football and Basketball prediction and value-detection tool: it estimates match outcome
probabilities with a Poisson model, compares them against real bookmaker
odds (de-vigged, so you're comparing against the *fair* market price), and
flags bets where your model disagrees enough with the market to be worth
tracking. It logs every pick, grades it once the match finishes, and gives
you an honest scorecard of whether it actually has an edge.

**Read this before you bet real money on anything it says:**

- No model, script, or "AI" reliably beats bookmakers long-term. Most don't.
  This tool is built to find out *whether yours does*, not to promise that it does.
- It ships in **paper mode** (`config.PAPER_MODE = True`) — it logs picks and
  simulated stakes only. Nothing here places real bets or requires real money
  to run.
- Don't flip to real staking until `metrics.py` shows a positive flat-stake
  ROI over 100+ *graded* bets. Anything smaller than that is statistical noise.
- Set a hard loss limit for yourself before you ever bet real money on this,
  independent of what the bot says. No staking algorithm protects you from
  betting more than you can afford to lose.

## 1. Get free API keys

- **API-Football** (fixtures + team stats): https://www.api-football.com/
  → free tier, 100 requests/day
- **The Odds API** (bookmaker odds): https://the-odds-api.com/
  → free tier, 500 requests/month

The Odds API aggregates major global bookmakers, not SportyBet/Bet9ja
directly — there's no public odds API for Nigerian platforms. Use it as a
"fair market" reference to compute edge, then compare/place on whichever
platform you actually use. Prices can differ slightly.

## 2. Install (Windows)

```cmd
cd footy_edge_bot
pip install -r requirements.txt
```

Paste your two API keys into `config.py`, or set them as environment
variables `API_FOOTBALL_KEY` and `ODDS_API_KEY` (safer — keeps keys out of
the file if you ever share it).

## 3. Run it

```cmd
python main.py
```

This fetches upcoming fixtures, runs the model, checks for value against
the market, and logs any bets found to `data/footy_edge.db`. It will very
often print "no value bets found" — that's expected and healthy. Real
edges are rare; a script that finds "value" in every match is broken, not lucky.

## 4. Grade results (run daily, after matches finish)

```cmd
python grade.py
```

Pulls final scores for your logged predictions and marks each WON/LOST.

## 5. Check honest performance

```cmd
python metrics.py
```

Shows Brier score (calibration accuracy), flat-stake ROI, Kelly-stake ROI,
and win rate by market — all computed only from graded (real, settled)
results. This is the number that matters, not the confidence % the model
printed beforehand.

## 6. Let it adapt (run weekly, once you have 50+ graded bets)

```cmd
python calibrate.py
```

Fits a recalibration curve mapping the model's raw probabilities to what
actually happened historically, and applies it to future predictions. This
is the "continually adapting" piece — it corrects systematic over/under-
confidence, it does not (and can't) guarantee improving profitability.

## Web dashboard (optional, but easier than the terminal)

Instead of running each script by hand, you can use a browser dashboard:

```cmd
python webapp.py
```

Then open **http://localhost:5000** on the host PC, or from any other
device on the same local network (e.g. your phone on the same hotspot),
open **http://<host-pc-local-ip>:5000** — find the host's IP with
`ipconfig` on Windows (look for the IPv4 address on your hotspot adapter).

This runs on `waitress`, a proper production-grade server (not the "do not
use in production" Flask dev server) — it's stable for regular local use.
If you ever need to debug a template/route issue directly, run
`set FOOTY_EDGE_DEBUG=1 && python webapp.py` (PowerShell:
`$env:FOOTY_EDGE_DEBUG=1; python webapp.py`) to get the Flask dev server's
auto-reload and debugger instead.

The dashboard has four pages:

- **Dashboard** — bankroll, quick stats, and buttons to run a scan, grade
  finished matches, or recalibrate, plus your most recent picks.
- **Predictions** — every pick ever logged, with full detail (model
  probability vs market probability, odds, bookmaker, result). Filter by
  result (won/lost/pending) or market, and export everything to CSV.
- **Metrics** — the same honesty dashboard as `metrics.py`, rendered as a
  page instead of terminal text.
- **Settings** — adjust minimum edge, Kelly fraction, days-ahead window,
  and which leagues to scan, without editing `config.py` or restarting the
  app. Changes apply on your next scan. (Paper/live mode is deliberately
  left out of this page — that switch stays in `config.py` on purpose, so
  it's never a one-click accident.)

Scan and grade now run in the background — clicking the button doesn't
freeze the page. The dashboard polls automatically and refreshes itself
once a job finishes.

## Adding NBA (basketball)

NBA support uses the same account you already have for football, so there's
no new signup:

1. Log into your existing dashboard at api-sports.io (the account behind
   your `API_FOOTBALL_KEY`). Find the **NBA** API in the product list and
   subscribe to its free plan -- it's a separate 100 req/day quota from
   football, tracked independently.
2. No new environment variable needed -- the app reuses `API_FOOTBALL_KEY`
   for NBA requests too (same key, same account, different product).
3. In Settings, check the "Basketball (NBA)" box under "Sports to scan" and
   save. Your next scan will cover both football and NBA.

**Scope note:** the NBA model currently covers the **moneyline (win/loss)
market only** -- no spreads or totals yet. It also skips a team until it
has at least 5 finished games this season to average from, so early in the
NBA season you may see nothing from it for a couple of weeks. It uses a
different (and simpler) model than football: expected point margin from
each team's recent scoring, converted to a win probability. Same underlying
principle as the football model -- compare model probability to the
de-vigged market price, only bet a real edge -- just built for a
higher-scoring, continuous sport instead of a low-scoring discrete one.

The field names this reads from API-Sports' NBA API (`teams.home/visitors`,
`scores.home.points/visitors.points`, game status codes `NS`/`FT`) are
based on their public documentation, not a live test call -- if your first
NBA scan errors out, check the actual response shape in the logs against
`nba_fetcher.py` and it's likely a quick field-name fix.

## Database on Render (Postgres)

Locally this uses a SQLite file at `data/footy_edge.db`. On Render's free
tier, local disk doesn't survive a redeploy or an idle restart, so deployed
instances should use Render's free Postgres database instead — `storage.py`
auto-detects it: if a `DATABASE_URL` environment variable is present, it
uses Postgres; otherwise it falls back to SQLite. No code changes needed
either way.

To use it: create a free Postgres database in the Render dashboard, then
either link it to the web service (Render adds `DATABASE_URL`
automatically) or copy its "Internal Database URL" into the web service's
own environment variables by hand.

## Locking the dashboard with a passcode

If the app is deployed somewhere reachable from your phone (not just your
LAN), set an `APP_PASSCODE` environment variable to lock it behind a login
page. It's a single shared passcode, not per-user accounts -- one code, one
session, no reset flow beyond changing the env var and redeploying.

- Not set (default): no login page, works exactly as before -- fine for
  local/LAN use.
- Set: every page redirects to `/login` until the correct passcode is
  entered. The session lasts 30 days, so you won't be asked constantly on
  your own phone. `/logout` clears it early if you want to.

## Automatic scheduling

In Settings, you can turn on "Run scan and grade automatically on a
schedule" and set daily times for each. While `python webapp.py` is
running, it'll fire the scan and grading jobs at those times without you
needing to click anything. This only works while the web app process is
open — it's not a separate background service, so if you close the
terminal/window running `webapp.py`, the schedule stops until you start it
again.

## Logs

Everything -- scans, grading, calibration, scheduled jobs, and any errors
-- gets logged to `logs/app.log` (rotated automatically, keeps the last
few MB). If something fails silently in the background, check there first.

## Running the test suite

The core math (the prediction model, value detection, and Kelly staking)
has an automated test suite covering it, so changes to those files can't
silently break the calculations:

```cmd
pip install -r requirements.txt
pytest tests/ -v
```

All tests should pass out of the box -- they test the pure math and don't
need API keys or internet access.

It's the same underlying engine as the command-line scripts — the buttons
just call `main.py`, `grade.py`, and `calibrate.py` for you. Nothing about
the paper-mode/real-money safeguards changes; they still apply here.

## Suggested weekly loop

1. `python main.py` — every day or two, to catch new fixtures
2. `python grade.py` — daily, once matches have finished
3. `python metrics.py` — whenever you want an honest read
4. `python calibrate.py` — weekly, once you have enough graded data

## What this can't do

- It can't get you Nigerian-platform-specific odds automatically (no public
  API exists for that) — you compare the flagged edge to your platform's
  actual price by hand.
- It can't guarantee profit. If `metrics.py` keeps showing flat or negative
  ROI after 100+ graded bets, that's the honest answer: no edge was found,
  and the responsible move is to stop, not increase stakes hoping variance
  turns around.
