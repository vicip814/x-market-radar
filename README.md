# X Market Radar

Focused market-intelligence dashboard for the X channels followed in this research thread.

It tracks AI infrastructure, semiconductors, memory/HBM, crypto, macro, policy trades, and market-data accounts.

## Channels

- `@aleabitoreddit` — Serenity / 白毛股神
- `@0xCryptoWizard` — 0xWizard / 巫师
- `@leopoldasch`
- `@qinbafrank`
- `@xiaomustock`
- `@maojietrading`
- `@morganhousel`
- `@charliebilello`
- `@ShanghaoJin`
- `@TrumpsPortfolio`
- `@artinmemes`
- `@unusual_whales`
- `@Beth_Kindig`

## How It Works

Vercel cannot reuse a local Chrome/X session. The live X refresh therefore runs locally through OpenCLI:

```bash
python3 aggregator.py --limit 8
```

That command writes `data.json`. The deployed site serves the latest committed snapshot through `/api/news` and falls back to `data.json` directly in the browser.

## Local Preview

```bash
python3 aggregator.py --limit 8
python3 -m http.server 8000
```

Open `http://localhost:8000`.

## Refresh Workflow

```bash
python3 aggregator.py --limit 8
git add data.json
git commit -m "Refresh X market snapshot"
git push
```

Vercel redeploys from GitHub after push.

For fully automated cloud refresh, add a proper X API token or another cloud-safe data provider and replace the local OpenCLI fetch path in `aggregator.py`.
