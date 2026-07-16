# Atlas Markets — multi-asset dashboard

A static, GitHub Pages–ready dashboard for cryptocurrencies, large-cap stocks, ETFs, index funds, major indices, commodities, and currencies. It includes calculators, local alerts, a diversified portfolio builder, allocation and performance tracking, and shareable portfolio links.

## Publish this repository with GitHub Pages

1. Upload **all files and folders in this package** to the root of `virkantt/spenekriptokurc`, preserving `.github/workflows`, `data`, and `scripts`.
2. Open the repository’s **Settings → Pages**.
3. Under **Build and deployment → Source**, choose **GitHub Actions**.
4. The included **Refresh data and deploy GitHub Pages** workflow runs on the first push, publishes the site, and then refreshes/deploys it hourly. You can also run it manually from the **Actions** tab.
5. The site will be available at `https://virkantt.github.io/spenekriptokurc/` after the first successful deployment.

## Enable CoinGecko crypto news

CoinGecko’s `/news` endpoint requires a paid CoinGecko API key with access to that endpoint. Keep the key out of `index.html`:

1. Open **Settings → Secrets and variables → Actions**.
2. Create a repository secret named `COINGECKO_API_KEY`.
3. Run the **Refresh data and deploy GitHub Pages** workflow.

Without the secret, the updater uses a GDELT crypto-news fallback. The browser’s optional CoinGecko Demo key setting is only for live crypto prices and charts; it does not unlock the paid news endpoint.

## How portfolio links work

The **Save & copy link** button serializes holdings, target allocations, the selected display currency, theme, and selected asset into a compact Base64URL payload after `#p=`. The URL fragment is processed in the browser. It is not a database and anyone with the link can view the encoded portfolio.

The app also auto-saves portfolio holdings, alerts, preferences, and calculator inputs in `localStorage` on the current device.

## Data architecture

- **Crypto prices and charts:** CoinGecko keyless/Demo API in the browser, with checked-in snapshots as fallback.
- **Stocks, ETFs, funds, indices, commodities, and FX:** an hourly GitHub Action writes `data/market-data.json` using Yahoo Finance chart snapshots.
- **Crypto news:** CoinGecko `/news` through the GitHub Action when `COINGECKO_API_KEY` is configured; GDELT fallback otherwise.
- **Global finance news:** GDELT DOC 2.0 queries for stocks, markets, macroeconomics, central banks, commodities, and ETFs.

Market data can be delayed, incomplete, or unavailable. Commodity symbols can represent futures contracts. This project is for informational use, not financial advice.

## Local preview

Because browsers restrict `fetch()` from `file://` pages, preview through a small local web server:

```bash
python -m http.server 8000
```

Then open `http://localhost:8000/`.

## Command-line upload

After extracting this package into the repository folder:

```bash
git add .
git commit -m "Launch Atlas Markets dashboard"
git branch -M main
git push -u origin main
```

Then select **Settings → Pages → Source → GitHub Actions**. The included workflow handles both data refreshes and deployment.
