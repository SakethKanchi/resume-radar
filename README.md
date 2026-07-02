# beating-resume-screeners

A [Claude Agent Skill](https://docs.claude.com/en/docs/agents-and-tools/agent-skills/overview)
that audits and optimizes a resume against automated **LLM resume-screening
agents**, reproducing the exact 120-point rubric from HackerRank's open-source
[`interviewstreet/hiring-agent`](https://github.com/interviewstreet/hiring-agent).

Modern screeners are not keyword ATS filters. They read the resume PDF, pull the
candidate's **live GitHub via API**, classify every repo as open-source vs
personal, and score four weighted categories plus bonuses and deductions. This
skill teaches Claude to see what the agent sees and to fix the highest-leverage
gaps, using **real signals and honest framing only**.

## What it does

- Reproduces the agent's GitHub classification (which caps the open_source
  score) with a zero-dependency Python script.
- Scores a resume against the full reverse-engineered rubric.
- Returns a gap table sorted by point-swing, plus concrete edits.
- Refuses to fabricate experience, PRs, stars, or metrics.

## Install

**Claude Code / claude.ai / API:** place this folder so `SKILL.md` sits at the
skill root (for Claude Code, drop it in `~/.claude/skills/beating-resume-screeners/`).
The skill auto-activates on prompts like "simulate my resume score" or "help me
beat the resume bot".

## Use

```
python scripts/github_enrich.py <github-username-or-url>
```

Set `GITHUB_TOKEN` to raise the GitHub API limit from 60/hr to 5000/hr. Then ask
Claude to `audit`, `simulate`, or `optimize` a resume.

## Contents

| Path | Purpose |
| --- | --- |
| `SKILL.md` | Skill instructions and workflow (loaded when triggered) |
| `references/RUBRIC.md` | Full 120-point rubric (loaded on demand) |
| `scripts/github_enrich.py` | Reproduces the agent's live GitHub classification |
| `scripts/test_github_enrich.py` | Offline unit tests for the script |
| `evaluations.json` | Behavioral evals for the skill |

## Ethics

This skill optimizes what a candidate genuinely has: it surfaces real merged
pull requests, adds working demo links, cleans up a cluttered GitHub, and
ensures real profile URLs are present. It never invents experience or
contributions. The screening agent reads the live repo and a human reads the
PDF, so dishonest signals get caught.

## Credit

Rubric reverse-engineered from the MIT-licensed
[`interviewstreet/hiring-agent`](https://github.com/interviewstreet/hiring-agent)
by HackerRank. This project is not affiliated with or endorsed by HackerRank.

## License

MIT
