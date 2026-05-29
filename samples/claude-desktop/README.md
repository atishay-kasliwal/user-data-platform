# claude-desktop

> The 60-second demo: point Claude Desktop at the public Hushh MCP
> endpoint and watch it read a consented vault scope.

This is the visceral version of the four invariants in
[`docs/04_principles.md`](../../docs/04_principles.md). You sign in,
approve a scope on your phone, and Claude answers questions about your
data — without the server ever seeing it.

## What you'll see

1. Claude asks about your data.
2. The Hushh consent flow fires a push notification to the Hushh app.
3. You tap approve in the app.
4. Claude returns the answer, citing the scope it received.

No data leaves your device unencrypted. The MCP server hands Claude
ciphertext; the connector inside the MCP runtime unwraps it.

## Setup (Claude Desktop, macOS)

1. Get a developer token at `https://uat.kai.hushh.ai/developers`.
2. Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
   and merge in the snippet from
   [`claude_desktop_config.example.json`](./claude_desktop_config.example.json).
3. Replace `<HUSHH_DEVELOPER_TOKEN>` with your token.
4. Restart Claude Desktop.

You should see a `hushh-consent` server appear in the MCP server list,
with tools like `discover_user_domains`, `request_consent`,
`check_consent_status`, `get_encrypted_scoped_export`.

## Try this

> *"Hushh, what scopes are available for me?"*
>
> *"Request consent to read `attr.financial.*` and summarize my recent losers."*
>
> *"What's the latest entry in `attr.personal.profile.*`?"*

The first time you ask, Claude will invoke `request_consent`. A push
arrives on your phone. Tap approve. Claude resumes and answers.

## Setup (Claude Code CLI)

```bash
claude mcp add --transport http hushh-consent \
  https://api.uat.hushh.ai/mcp/?token=<HUSHH_DEVELOPER_TOKEN>
```

Then start a session and ask the same questions.

## What is not included

- A pre-recorded screencast. The whole point is that the user runs
  this themselves in 60 seconds. We can capture one if useful.
- A self-hosted MCP runtime. Use the public UAT endpoint or, for stdio
  hosts, see the [`@hushh/mcp` npm bridge docs](https://www.npmjs.com/package/@hushh/mcp).

## Why this matters

Compared to the `samples/external-agent` Python demo, this one needs
zero code from the developer. Claude is already an MCP host. The user
config is six lines. The trust contract still holds: every read goes
through the consent prompt, the server only sees ciphertext, and every
access leaves a receipt in `pkm_events`.

That is roughly the shortest possible path from "I have a token" to
"my AI assistant safely reads my data."
