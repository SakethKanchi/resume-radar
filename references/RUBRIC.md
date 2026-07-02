# hiring-agent scoring rubric (reverse-engineered)

Full rubric extracted from `interviewstreet/hiring-agent` (HackerRank's
open-source resume scorer). Source templates:
`prompts/templates/resume_evaluation_criteria.jinja`,
`resume_evaluation_system_message.jinja`, `github_project_selection.jinja`;
scoring math in `score.py` / `evaluator.py`.

## Contents
- Pipeline overview
- Score formula and caps
- Category: open_source (0-35)
- Category: self_projects (0-30)
- Category: production (0-25)
- Category: technical_skills (0-10)
- Bonus points (<=20)
- Deductions
- Fairness firewall
- GitHub project selection rules

## Pipeline overview

1. PDF to Markdown via PyMuPDF. Text must be selectable, not an image.
2. LLM extracts sectioned JSON (basics, work, education, skills, projects,
   awards). Only URLs literally present in the resume are extracted.
3. GitHub enrichment: username is pulled from the resume, the GitHub API is
   called, repos are classified, and the LLM picks the top 7.
4. LLM scores four categories + bonus - deductions, capped at 120.

## Score formula and caps

```
total = sum(min(category_score, category_max) for the 4 categories)
        + min(bonus_total, 20)
        - deductions_total
total = min(total, 120)   # 100 category max + 20 bonus
```

Category maxes: open_source 35, self_projects 30, production 25,
technical_skills 10.

## Category: open_source (0-35)

- 25-35: contributions to popular OSS (1000+ stars), significant
  contributions, Google Summer of Code (GSoC).
- 15-24: contributions to smaller OSS projects; meaningful contributions to
  other people's repos.
- 5-10: only personal repos; minimal OSS activity.
- 0-4: no GitHub, or only trivial personal repos.

Hard rules:
- Personal repositories do NOT count as open source. True OSS means
  contributing to OTHER people's projects (a repo with >1 contributor).
- If GitHub data shows every repo is `self_project` type, open_source MUST be
  <= 10.
- Hacktoberfest participation alone (without evidence of real contributions)
  is 3-5 points max and triggers a 3-5 point deduction.

## Category: self_projects (0-30)

- 20-30: complex projects, real-world impact, advanced architecture, multiple
  technologies, user adoption.
- 10-19: some complexity, good documentation, multiple features.
- 1-9: tutorial projects (todo, calculator, weather app, notes, basic CRUD,
  NLTK/sklearn sentiment), classroom assignments.
- 0: basic CRUD applications.

Link modifiers:
- No link (no repo, no demo, no active URL): 30-50% lower, and -3 to -5 per
  project.
- GitHub link but no live demo: -2 to -3 per project.
- Broken/inactive link: -1 to -2 per project.
- Working live demo: +10 to 20%.

## Category: production (0-25)

Work, internship, and volunteer experience. Founder / co-founder / early-stage
engineer (first 10-20 employees) gets extra points for building products from
scratch.

## Category: technical_skills (0-10)

Breadth of languages and frameworks, and evidence of problem-solving in
projects, work, or competitions.

## Bonus points (total <= 20)

- +5 Google Summer of Code (GSoC)
- +3 Girl Script Summer of Code
- +3-5 startup founder / co-founder
- +2-3 early-stage engineer (first 10-20 employees)
- +2 portfolio website (a portfolio/personal URL present in basics)
- +1 LinkedIn profile present
- +1-3 high-quality technical blog (only if a blog URL is present so the agent
  can fetch it)

## Deductions

- -2 to -5 if the resume contains only simple tutorial projects.
- -1 to -3 for each simple project beyond the first.
- -1 for generically named projects ("Calculator", "Todo App", "Weather App").
- -2 if all projects are classroom assignments or tutorial-based.
- -3 to -5 per project with no link at all.
- 3-5 point open_source deduction if all repos are self_project or the only
  OSS signal is Hacktoberfest.

## Fairness firewall (do not optimize here)

The prompts HARD-FORBID scoring on name, gender, school/university, GPA/CGPA,
city/location, or any demographic. Adding a prestigious school or high GPA does
not raise the score. Spend that resume space on signal instead.

## GitHub project selection rules

From `github.py` and `github_project_selection.jinja`:
- Forks with `forks_count < 5` are skipped.
- `project_type = "open_source" if contributor_count > 1 else "self_project"`.
- A repo is eligible as a top project only if the candidate's own
  `author_commit_count` is >= 4. Repos with 1-3 of the candidate's commits are
  ignored.
- The LLM selects the top 7 eligible repos, favoring popular-OSS contributions
  and high commit counts.
- The agent fetches up to 100 repos sorted by stars, so unpinned toy repos are
  still seen and can trigger deductions.
