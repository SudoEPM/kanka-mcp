---
name: prep
description: Prep the current branch (or pending main edits) for review — surface manual verification first, open as draft, run a Copilot review iteration with respectful pushback, decide when a second review is worth requesting, then flip to ready. Invoke as /prep.
argument-hint: (none — operates on the current branch or pending edits on main)
---

# Prep skill — kanka-mcp

Drives a feature/fix from "code is written" to "PR ready for merge" — adapted for this repo's Python MCP-server shape (no CI workflow, single-user repo, Kanka REST as the external contract).

The skill has 11 steps. Stop after step 11 — **do not poll merge state**, the user merges when satisfied.

## Step 0 — Branch resolution

This repo is solo-dev and changes often start uncommitted on `main`. Handle the four cases up front:

```bash
BRANCH=$(git rev-parse --abbrev-ref HEAD)
git fetch origin main >/dev/null 2>&1
DIRTY=$(git status --porcelain | wc -l | tr -d ' ')
AHEAD=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
```

- **`BRANCH == main`, `DIRTY == 0`, `AHEAD == 0`**: nothing to prep. Stop, tell the user.
- **`BRANCH == main`, `DIRTY > 0`**: auto-create a branch from the dominant topic of the working-tree diff (e.g. status migration → `feat/status-id-migration`). Print the name to the user as a checkpoint, then `git checkout -b <branch>`. Don't gate on confirmation; they can interject.
- **`BRANCH == main`, `AHEAD > 0`**: rare, but `git checkout -b <branch>` from main (preserving commits), then `git reset --hard origin/main` on the original main checkout. Actually — safer: ask the user. This is the one edge case that warrants an `AskUserQuestion`.
- **`BRANCH != main`**: continue.

Then check whether a draft PR already exists for the branch:

```bash
gh pr view --json number,isDraft,title,url 2>/dev/null
```

- **PR exists, draft**: skip step 3 (already opened); resume at step 4 (Copilot wait) or step 5 (address feedback) depending on whether a Copilot review has already landed.
- **PR exists, ready**: stop, ask the user — they probably want `/prep` for a different branch.
- **No PR**: continue.

## Step 1 — Survey the branch

```bash
git log --oneline origin/main..HEAD
git diff --stat origin/main..HEAD
```

Internalize the change-set shape — file types touched determine the verification checklist in step 2.

## Step 2 — Manual verification gate

Propose a focused checklist of items the user should manually verify before the PR opens — **not** a full QA pass, just the things this diff specifically risks regressing. Use file types as a guide:

- **`kanka/entities/*.py`** tool signature changes (params added/removed/renamed, defaults changed): if the param dropped is one Claude Desktop was passing, existing prompts break. Verify the tool still callable from Claude Desktop with a one-line smoke (e.g. "get me all creatures" or "set X's status_id to Y").
- **`kanka/server.py`** registration changes (new entity module wired in): run `.venv/bin/python -c "from kanka import server; print('OK')"` — must succeed, or MCP won't boot.
- **Kanka API contract changes** (added/removed/renamed fields against `/api-docs/1.0/...`): hit the affected endpoint via curl with the campaign creds in `.env` and confirm the field name on the live response matches what the code sends.
  ```bash
  set -a && source .env && set +a
  curl -s -H "Authorization: Bearer $KANKA_API_TOKEN" -H "Accept: application/json" \
    "https://api.kanka.io/1.0/campaigns/$KANKA_CAMPAIGN_ID/<endpoint>?per_page=1" | python3 -m json.tool | head -50
  ```
- **`kanka/client.py`** changes (auth, base URL, request shape): confirm `.env` resolution still works and one read endpoint round-trips.
- **`CLAUDE.md` / `README.md`** prose-only changes: no smoke needed beyond proofread.

Present via `AskUserQuestion` with two options:
- **"Verified — proceed"** (recommended)
- **"Bypass — I'll verify after merge"**

Do not silently skip this step. The whole point is to make the user pause before opening a PR they'd regret. With no CI, this gate is *more* important than in sibling repos, not less.

## Step 3 — Commit pending work, draft PR metadata, push + open

After step 2, the skill runs hands-off through to step 9. **No more `AskUserQuestion` calls between here and step 9** — print decisions and proceed.

**Commit pending work first.** If the working tree has uncommitted changes relevant to this branch, commit them as a single conventional-commit-shaped commit. Pick the prefix from the dominant nature of the changes (`feat:` new tool/entity, `fix:` API drift / bugfix, `chore:` infra, `refactor:` internal restructure, `docs:` README/CLAUDE.md). Stage explicit paths — not `git add -A` — to avoid pulling in `.env` or stray local files.

Skip straight to PR metadata if the tree is clean.

**Compose PR metadata** from the commit log:

```bash
git log --format='%s%n%n%b' origin/main..HEAD
```

Title: a single conventional-commit-shaped sentence summarizing the branch (≤70 chars). Body: a `## Summary` section with the substantive bullets, followed by a `## Test plan` checklist mirroring step 2's verification items. Print the title + body to the user as a visibility checkpoint — *don't* prompt; they can interject if they want a change.

**Pick the label** from the conventional-commit prefix on the lead commit:
- `feat:` → `enhancement`
- `fix:` → `bug`
- `docs:` → `documentation`
- `chore:` / `refactor:` / other → `enhancement` (no `chore`/`tech-debt` label exists in this repo's default set; `enhancement` is the catch-all)

**Push and open as draft:**

```bash
git push -u origin "$BRANCH" 2>&1 | tail -3
gh pr create --draft --label <label> \
  --title "<title>" --body "$(cat <<'EOF'
<body>
EOF
)"
```

Capture `PR_URL` and `PR_NUM` from the create output.

## Step 4 — Wait for the first Copilot review

Copilot fires once on PR-open (works on drafts), takes ~5–7 minutes, doesn't re-fire on subsequent pushes. For PRs targeting non-`main` bases auto-fire is unreliable — manually request first.

```bash
BASE=$(gh pr view $PR_NUM --json baseRefName --jq .baseRefName)
if [ "$BASE" != "main" ]; then
  gh pr edit $PR_NUM --repo mike-levenick/kanka-mcp --add-reviewer @copilot
fi
```

Poll in the background (use `Bash` with `run_in_background: true`, or `Monitor`):

```bash
i=0
while true; do
  count=$(gh api repos/mike-levenick/kanka-mcp/pulls/$PR_NUM/reviews 2>/dev/null \
    | jq '[.[] | select(.user.login | test("copilot"; "i"))] | length')
  if [ "$count" -gt 0 ]; then
    echo "Copilot review landed after $((i*30))s"
    break
  fi
  if [ $i -ge 24 ]; then
    echo "Timed out after 12 min — re-check; if Copilot didn't fire, request via gh pr edit --add-reviewer @copilot"
    break
  fi
  i=$((i+1))
  sleep 30
done
```

Once it lands, fetch and display:

```bash
# Top-level review (overview + state)
gh api repos/mike-levenick/kanka-mcp/pulls/$PR_NUM/reviews \
  --jq '.[] | select(.user.login | test("copilot"; "i")) | "STATE: \(.state)\nSUBMITTED: \(.submitted_at)\nBODY:\n\(.body // "(none)")\n---"'

# Inline comments (with comment IDs we need for replies)
gh api repos/mike-levenick/kanka-mcp/pulls/$PR_NUM/comments \
  --jq '.[] | select(.user.login | test("copilot"; "i")) | "ID: \(.id)\nFILE: \(.path):\(.line // .original_line)\nBODY: \(.body)\n---"'
```

Bot-login quirk: `/reviews` returns `copilot-pull-request-reviewer[bot]`, `/comments` returns `Copilot`. The case-insensitive substring filter (`test("copilot"; "i")`) catches both.

## Step 5 — Address the feedback

For each inline comment, decide one of three:

1. **Fix it.** Make the change, batch into commits with the rest. **Do not reply** — "Fixed in <SHA>" replies are noise. The fix commit is the documentation.

2. **Push back.** When Copilot is wrong (false-positive about a syntax/runtime concern, suggests an idiom that contradicts the project's pattern), reply respectfully with reasoning. Use the comment's `id` from step 4:

   ```bash
   gh api repos/mike-levenick/kanka-mcp/pulls/$PR_NUM/comments \
     -X POST \
     -f body="<respectful reply with reasoning>" \
     -F in_reply_to=<COMMENT_ID>
   ```

   Tone: collegial, evidence-based. Cite the commit SHA or file:line that backs the call.

3. **Defer.** Real concern but out of scope. Reply with the deferral and reasoning, optionally file an issue and reference it.

Track decisions in a running list — step 9's report needs them.

After the address pass:

```bash
git push 2>&1 | tail -3
```

## Step 6 — Decide on a second review

Be honest, not optimistic.

**Worth requesting** if any of:
- The fix commit added genuinely new logic (not just a rename, comment, or 1-line tweak).
- The fixes touched a different concern than the original review covered.
- A first-pass concern was deferred and you want a second opinion on the deferral.

**Skip** if:
- All fixes were mechanical (renames, dead-code removal, docstring tweaks).
- All fixes are within the same surface Copilot already reviewed.
- You pushed back on most comments and want to ship.

State the call to the user explicitly: "I think a second pass is/isn't warranted because <reason>."

If skipping, jump to step 9.

## Step 7 — Re-request review

Copilot does NOT auto-re-fire on subsequent pushes. Request manually:

```bash
gh pr edit $PR_NUM --repo mike-levenick/kanka-mcp --add-reviewer @copilot
```

The literal `@copilot` (with `@`) is required — without it `gh` silently dedups since Copilot already reviewed an earlier SHA.

## Step 8 — Wait for and address the second review

Reuse the polling from step 4 and the address-feedback flow from step 5.

After this pass, **do not request a third round** unless one of these holds:
- You strongly believe Copilot will catch new material issues.
- The user explicitly asks for another round.

The diminishing-returns curve is steep — pass 3 typically surfaces 0–2 nits with no real bugs. Default to stopping.

## Step 9 — Final report

Print a summary to the user with:

- **Tweaks made**: bulleted list of substantive changes from the Copilot iterations.
- **Pushback**: bulleted list of comments where you disagreed, each with one-line reasoning. This is the most useful part — judgment calls the user should sanity-check.
- **Deferred**: bulleted list of comments deferred to follow-up, with issue numbers if filed.

Format:

```
## Tweaks landed
- <bullet>
- <bullet>

## Pushback
- <comment topic>: <reasoning>

## Deferred
- <comment topic> → issue #N (or: noted but no issue filed)
```

## Step 10 — Flip to ready

```bash
gh pr ready $PR_NUM
```

There's no CI workflow in `.github/workflows/`, so this doesn't trigger a build — it just signals "iteration done, mergeable on your time."

## Step 11 — Stop

Tell the user the PR is ready, link the URL, stop. Do not poll merge state — they'll come back when they've merged or want a follow-up.

## Common pitfalls — re-check before each step

- **Don't post "Fixed in <SHA>" replies.** Only reply when disagreeing or deferring. The commit speaks for itself.
- **Don't bypass the verification step** without surfacing it. With no CI here, step 2 is the only safety net before the change lives on main.
- **Don't reintroduce check-ins between steps 2 and 9.** Beyond step 2, hands-off: commit, open, iterate, flip. Print decisions inline; let the user interject.
- **Don't `git add -A`.** Stage explicit paths so `.env` and stray locals don't leak.
- **Don't run a third Copilot pass by reflex.** Trust the user to ask.

## References

- `CLAUDE.md` → project conventions (Kanka API doc links, CRU-not-CRUD tool policy).
- Kanka API: `https://app.kanka.io/api-docs/1.0/<entity>` — the source of truth when the verification step needs to confirm a field name.
