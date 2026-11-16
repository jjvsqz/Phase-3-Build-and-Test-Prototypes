# CRAVD — Phase 3 playable prototype

**Good food. Better together.** This is a classroom-ready, **three-or-more-person social interaction prototype**, not a production dining application.

## What this demonstrates

A college student discovers that two friends have saved the same campus food item as a favorite. The student invites those friends to lunch **before either friend is online**. The friends join later and RSVP independently; the group negotiates a common time, confirms the plan, and simulates lunch. Everyone then contributes a *quick personal reaction* to a single collaborative review. There are **no stars, weighted rankings, or venue scores**.

The distinctive social loop is **friends' food preferences → asynchronous invitation → negotiated shared plan → collective meal memory**. This is a design hypothesis to evaluate, not a claim that every component is novel.

## Quick start on your laptop

Requires **Python 3.10+** and internet access *only* if you need to install packages.

```bash
cd cravd_phase3
python -m pip install -r requirements.txt
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Open **http://127.0.0.1:8000/**. On Windows, you may use `py` instead of `python`. For a basic local network demonstration, start with `--host 0.0.0.0` and use the laptop's LAN IP, but devices must be on the same network and its firewall must permit the connection. **`localhost` is not accessible to classmates on their own devices.**

### Setting up the shared role-play

1. A facilitator opens the home page and clicks **Create new room**.
2. Copy the **instructions link** from the room screen. Example: `https://YOUR-DEPLOYMENT/guide?room=AB3CD5`.
3. Share that link with **at least three classmates**. They open the linked prototype and join the *same* six-character room as User01, User02 and User03.
4. The User01 tester starts first; they open **Friends' Favorites** and invite User02 + User03 to the pizza that both have saved.
5. User02 and User03 can join afterward, open **Lunch Plans**, and respond. User01 then confirms a time accepted by everyone.
6. User01 clicks **We've finished lunch** to simulate passage of time. All three submit their own short reaction and may upvote one another.
7. Participants complete the feedback survey independently.

User04 is available if more students wish to participate. Every room has its own separate shared state. Opening the same room on different devices enables meaningful multi-person interaction; these are not isolated browser mockups.

## Publishing one public URL for the class

Your code must run on a reachable web server for three students on different devices to exchange information. **This ZIP does not itself provide a live public URL.**

A straightforward option is a Python-capable host such as Render:

1. Upload this project folder to a **GitHub repository**.
2. Create a **Python web service** connected to that repository (or deploy the supplied `render.yaml` blueprint if supported by your account).
3. Configure build command: `pip install -r requirements.txt`.
4. Configure start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`.
5. Set the optional environment variable `SURVEY_URL` to the real Google Forms feedback URL, e.g., `https://docs.google.com/forms/d/e/.../viewform`.
6. Open the resulting public HTTPS service, create a room, and share `/guide?room=XXXXXX` as your **one classroom session link**.
7. **Before presenting:** open the link on *three distinct devices* and run a complete rehearsal. Test link permissions and whether the host takes time to wake up.

**Important persistence limitation:** the default database is a local SQLite file. Many starter web hosts have **ephemeral filesystems** that can reset on deployment/restart; a room could disappear after a service restart. For a 25-minute classroom demo, avoid redeploying or restarting the service mid-session. For more dependable hosting, use a persistent disk or migrate the same shared state to a managed database. Use **a single worker** for this small prototype.

## Files

- `app.py` — FastAPI server, SQLite shared state, role joining, invitations, RSVP, chat, reviews, privacy.
- `static/index.html`, `static/style.css`, `static/app.js` — mobile-friendly interface, no frontend build required.
- `static/guide.html` — public scenario, roles, instructions, and feedback-survey link.
- `docs/roleplay_instructions.md` — full facilitator and role-play instructions.
- `docs/evaluation_plan.md` — questions, evidence, observable metrics, anticipated emergent behavior.
- `docs/feedback_survey.md` — non-leading post-session survey you can paste into Google Forms.
- `docs/facilitator_checklist.md` — running a 25-minute session.
- `docs/round2_iteration_plan.md` — what to change and compare for Week 10.
- `docs/intro_slide_text.md` — ready-to-copy introduction slide wording.
- `tests/test_scenario.py` — API end-to-end test (three roles).
- `tests/browser_check.py` — browser-backed integration test used in this environment; uses a local transport shim due to sandbox browser networking restrictions.
- `render.yaml` and `Procfile` — deployment starters.

## Test the shared behavior

```bash
python tests/test_scenario.py
```

The test makes a room, sends an invitation *before* two friends join, has each friend RSVP, blocks confirmation of a time not accepted by all, confirms a common time, posts independent group reactions, tests upvotes, and verifies favorite-list privacy.

## Scope, privacy, and future product decisions

All demo locations, dishes, calendars, participants and favorites are **synthetic**. We deliberately use no real student identifiers, university credentials, private contact lists, or live location. The classroom sign-in uses role tokens in the browser and is **not** production-grade authentication. Don't collect sensitive or real personal information in demo comments. Don't publish sensitive class data.

Unresolved design questions to investigate: who sees a student's favorites; whether people want to share their free times or only RSVP; what happens if a seasonal menu item disappears; whether time negotiation is easier inside or outside the app; whether a shared review feels meaningful or obligatory; and whether students want only friends or also classmates in the discovery feed. These are research questions, not built-in claims.

### What to test vs. what to defer

**Round 1:** preference visibility, offline invitations, group time selection, low-friction after-lunch reactions. Observe genuine social negotiation.

**Future/optional:** availability validation against live UCSD menus, real university authentication, calendar sync, photo storage, push notifications, and multi-campus expansion. Only implement these if user research supports them.
