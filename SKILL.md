---
name: beating-resume-screeners
description: >-
  Audits and optimizes a resume against automated LLM resume-screening agents,
  reproducing the exact 120-point rubric from HackerRank's open-source
  hiring-agent (interviewstreet/hiring-agent). Unlike a keyword ATS, that
  screener reads the resume PDF, pulls the candidate's live GitHub via API,
  classifies each repo as open-source vs personal, and scores four weighted
  categories plus bonuses and deductions. Use when a user wants to beat resume
  bots, pass automated screening, "bypass the ATS", get noticed by recruiters,
  simulate their resume score, audit a resume against a known rubric, or tune
  their GitHub and projects to score higher. Triggers include "hiring agent",
  "resume score", "ATS bypass", "resume bot", "automated screening", and "rank
  my resume". Optimizes real signals and honest framing only; it never
  fabricates experience, contributions, or metrics.
license: MIT
compatibility: Requires Python 3.8+ and internet access to the GitHub REST API. A GITHUB_TOKEN env var is optional but raises the rate limit from 60/hr to 5000/hr.
---

# Beating Resume Screeners

Optimize a resume to win against LLM resume-scoring agents. The rubric here is
reverse-engineered from HackerRank's open-source `interviewstreet/hiring-agent`,
which many companies now run or imitate. Winning is not keyword stuffing; it is
maximizing the specific signals the LLM is told to reward and removing the ones
it is told to punish.

## Core mental model (read first)

This is not a legacy keyword ATS. The screener:

1. Converts the resume PDF to text. Text must be selectable, never an image.
2. Extracts sections with an LLM. It only extracts URLs literally present in
   the resume, so a missing LinkedIn, portfolio, or blog URL loses bonus points.
3. Pulls the candidate's live GitHub from the username on the resume, then
   classifies every repo: `open_source` if a repo has more than one
   contributor, else `self_project`. A repo counts as a top project only if the
   candidate has 4 or more commits on it.
4. Scores four categories, adds bonus, subtracts deductions, caps at 120.

Key consequence: the candidate's live GitHub is graded whether they like it or
not. The GitHub URL on the resume is a lever, not decoration.

## Scoring at a glance

| Category | Max | What drives it |
| --- | --- | --- |
| open_source | 35 | contributions to OTHER people's repos; popular-OSS PRs; GSoC |
| self_projects | 30 | project complexity, real impact, working live demos |
| production | 25 | work / internship; founder or early-stage engineer roles |
| technical_skills | 10 | breadth of languages and frameworks |
| bonus | <=20 | GSoC, founder, portfolio URL, LinkedIn, blog |

Full point breakdown, caps, and every deduction: see [references/RUBRIC.md](references/RUBRIC.md).

## Highest-leverage fixes (ranked)

1. **Fix open_source (up to +25).** Personal-repo-only profiles are capped at
   ~10/35. Earn real points with a merged PR to a popular repo (1000+ stars),
   or a genuine second contributor on an existing project so it reclassifies as
   `open_source`. Surface merged PRs the resume never mentioned.
2. **Add a working live demo URL to every project** (+10-20% on self_projects;
   avoids -3 to -5 per unlinked project).
3. **Ensure the resume's GitHub username is exact and top repos have 4+ of the
   candidate's commits.** Archive or make private the toy repos (todo,
   calculator, weather clones) that trigger generic-name deductions.
4. **Keep founder / early-stage framing explicit** (+3-5 bonus plus production
   points): use literal terms like "Founding Engineer" or "first N employees".
5. **Put LinkedIn, portfolio, and blog URLs literally on the resume** (up to
   +6 bonus). A fetchable blog adds technical-communication signal.
6. **Do not optimize school, GPA, or location.** The rubric forbids scoring on
   them. That space is better spent on signal.

## Workflow

Pick a mode from the request; default is `audit`.

```
Progress:
- [ ] 1. Read the resume; note the GitHub username and every URL present
- [ ] 2. Run github_enrich.py to reproduce the agent's GitHub classification
- [ ] 3. Score all four categories + bonus - deductions per references/RUBRIC.md
- [ ] 4. Report the gap table, sorted by point-swing
- [ ] 5. (optimize mode) apply real, honest fixes and re-score
```

### Step 1: Read the resume

Extract text and record the GitHub username plus which of {LinkedIn, portfolio,
blog} URLs are literally present. Missing URLs are free bonus points left on
the table.

### Step 2: Reproduce GitHub classification

The classification, not the resume text, determines the open_source ceiling.
Run the bundled script (standard library only, no install):

```bash
python scripts/github_enrich.py <github-username-or-url>
```

Set `GITHUB_TOKEN` to raise the API limit from 60/hr to 5000/hr. Output is JSON
with per-repo `project_type`, the candidate's commit count, and
`open_source_cap_triggered` (true when every owned repo is `self_project`,
which caps open_source at ~10/35).

Critically, the script also reports `external_merged_pr_count` and
`external_merged_prs`: merged PRs the candidate made to OTHER people's repos.
This is the strongest open_source signal in the rubric, and the screener's
owned-repo scan does not see it. When `hidden_open_source_signal` is true, the
candidate is being under-scored: the fix is to LIST those PRs on the resume
(with repo name and star count) so the agent credits them, not to accept the
cap.

### Step 3: Score against the rubric

Apply [references/RUBRIC.md](references/RUBRIC.md) literally and be strict; the
agent's prompt is skeptical of personal repos. Quantify every line in points.

### Step 4: Report the gap table

Emit each category as current vs realistic ceiling with the one action that
closes the gap, sorted by point-swing, then the projected total /120. In
`simulate` mode, also emit the JSON the agent would produce (scores with
evidence, bonus, deductions, key_strengths, areas_for_improvement) and a final
`OVERALL SCORE: X/100`.

### Step 5 (optimize mode only): apply fixes and re-score

Make the concrete edits: rewrite bullets, add live-demo URLs, list real merged
PRs, archive toy repos, add missing profile URLs. For LaTeX resumes, show the
diff and rebuild. Re-run Step 2 and re-score to show the projected new total.

## Hard rules

- Optimize real signals and honest framing only. Never invent jobs,
  contributions, PRs, stars, or metrics. The agent reads the live repo and
  humans read the PDF.
- Always quantify advice in points (for example "+~15 open_source"). Vague
  advice is useless against a numeric rubric.
- Lead with the single highest-leverage fix. For most software candidates that
  is open_source.
