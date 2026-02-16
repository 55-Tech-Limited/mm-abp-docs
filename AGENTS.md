# Documentation project instructions

## About this project

- This is the **55-Tech API Documentation** site built on [Mintlify](https://mintlify.com)
- Covers two APIs: **ABP** (Automated Bet Placing) and **MM** (Market Making)
- Pages are MDX files with YAML frontmatter
- Configuration lives in `docs.json`
- OpenAPI specs live in `abp-api/openapi.json` and `mm-api/openapi.json`
- Run `mint dev` to preview locally
- Run `mint broken-links` to check links

## Terminology

- Use "ABP" for Automated Bet Placing
- Use "MM" for Market Making
- Use "bookmaker" not "sportsbook" or "bookie"
- Use "exchange" for prediction market platforms (Polymarket, Kalshi)
- Use "fixture" for sports events/matches
- Use "order" for client-initiated bet instructions
- Use "bet" for actual wagers placed on bookmakers
- Use "OddsPapi" (capital P) for the data provider

## Style preferences

- Use active voice and second person ("you")
- Keep sentences concise — one idea per sentence
- Use sentence case for headings
- Bold for UI elements: Click **Settings**
- Code formatting for file names, commands, paths, and code references
- Follow the same patterns as the [OddsPapi docs](https://docs.oddspapi.io/)

## Content boundaries

- Document all client-facing API endpoints
- Document WebSocket protocols and channels
- Do not document internal admin implementation details
- Do not expose actual API keys or credentials in examples
