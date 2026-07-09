# DC24 Job Card App

A phone-friendly job card matching your existing DC24 paper job card/safe disposal certificate:
technician fills in the job details, the client (plus driver and disposal site) sign on screen, and
the completed job card is emailed to your office automatically — no manual step, no app store install.

## What's included

- `public/index.html` — the job card form technicians use (works in any phone browser), laid out
  to match the paper DC24 job card: customer details, Planon number, job description, Job Type /
  Drain Type / Liquid Waste / Pump Out / Consumables / Waste Stream / Waste Type checklists, quote
  requirements, before & after photos, Customer and Driver sign-off, a Yes/No safe disposal
  certificate question, comments, service rating, and date/time in-out (with a second visit slot)
- `server.py` — a small Python server that receives submitted job cards, assigns the next job
  number, and emails everything via your real SMTP account (Gmail, Outlook/365, or your existing
  business mail server)
- `config.example.json` — template for your SMTP settings and starting job number
- `sequence.json` — created automatically the first time the app is used; tracks the next job
  number so it survives server restarts

No external packages are required — everything runs on Python's standard library.

## Automatic job numbering

Every technician's phone talks to the same server, so job numbers stay in one true sequence no
matter who's filling out a card or how many are open at once. The moment a technician opens a new,
blank job card, the app asks the server for the next number and reserves it immediately — that's
why the badge at the top of the screen shows a number right away rather than a blank field. As soon
as that card is submitted, the very next job card anyone opens (on any phone) will show the
following number.

**Setting your real starting number:** you mentioned you'll provide the number to start from when
ready. When you have it:

1. Stop the server if it's running.
2. Delete `sequence.json` if one already exists (it may have been created during testing).
3. Set `"START_JOBNO"` in `config.json` to your real starting number (e.g. `37103`, matching where
   your paper books left off).
4. Restart `python3 server.py` — the first job card opened will show that exact number, and it'll
   count up from there.

If `sequence.json` already exists, the value in `config.json`'s `START_JOBNO` is ignored (the
server trusts the persisted sequence over the config default) — so deleting it is the key step
when you want to reset the starting point.

## Setup (5-10 minutes)

**1. Copy the config template and fill in your real details:**

```
cp config.example.json config.json
```

Open `config.json` and fill in:

| Field | What to put |
|---|---|
| `SMTP_HOST` | Your mail server, e.g. `smtp.gmail.com`, `smtp.office365.com`, or your host's mail server |
| `SMTP_PORT` | Usually `587` (TLS) — see notes below for Gmail/Office 365 |
| `SMTP_USE_TLS` | `true` for port 587 (standard) |
| `SMTP_USE_SSL` | `true` only if using port `465` instead |
| `SMTP_USER` | The email address that will send the job cards |
| `SMTP_PASSWORD` | See the important note below — **do not use your normal login password for Gmail/Office 365** |
| `EMAIL_FROM` | Usually the same as `SMTP_USER` |
| `EMAIL_TO` | Where completed job cards should land, e.g. `office@leakfind.co.za` |
| `COMPANY_NAME` | Shown in the email heading |

**Never share `config.json` with anyone or commit it to any public repository — it contains your
email password.** It's a plain local file that only needs to exist on the computer/server running
`server.py`.

**2. Gmail and Outlook/365 both require an "app password", not your normal password:**

- **Gmail**: turn on 2-Step Verification, then create an App Password at
  [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) — use that
  16-character code as `SMTP_PASSWORD`. Host: `smtp.gmail.com`, port `587`.
- **Outlook/365**: create an app password under Security settings in your Microsoft 365 account.
  Host: `smtp.office365.com`, port `587`.
- **Your own hosting provider's email** (e.g. if Leakfind's email runs through your web host):
  ask your host for their SMTP host/port — usually your normal email password works there, no app
  password needed.

**3. Run the server:**

```
python3 server.py
```

It prints two addresses:
```
Local:   http://localhost:8000
Network: http://192.168.x.x:8000
```

Open the `Network:` address on a technician's phone (same wifi) to test it. For technicians to use
this in the field (not just on office wifi), the server needs to run somewhere reachable from
outside your office network — see "Going live" below.

## Using the app

1. Technician fills in job details, description of work, and any materials used.
2. Optional: attach before/after photos from the phone camera.
3. Client and driver sign directly on the phone screen.
4. Technician answers **"Is this job card linked to a disposal site certificate?"** (Yes/No).
5. Tap **Complete Job Card** — the email sends immediately in the background to
   `info@drainclean24.co.za` (or whatever `EMAIL_TO` is set to). If the customer's email address
   was filled in and looks valid, they automatically get their own copy too (subject "Your Job
   Card #...") — sent in addition to, never instead of, the office copy. A missing or badly
   typed client email just skips that copy quietly; it never blocks the job card itself from
   going through.
6. A thank-you screen appears with a **⭐ Rate DC24 on Google** button — handy to hand the phone to
   the client right there on site while the job is fresh. Tapping **Start Next Job Card** dismisses
   it and loads the next job number.
7. If there's no signal at the moment of submission, the job card is saved in the phone's local
   **History** tab with a "Failed" tag and a **Resend** button, so nothing is lost — just resend
   once back in signal range. The thank-you/review screen still appears either way, since the job
   itself is done regardless of whether the email sent immediately.

## Safe disposal certificate follow-up

If a technician answers **Yes** to the disposal certificate question, the job card shows up in the
**History** tab flagged red, with "Safe Disposal Required: Yes — awaiting certificate". This is a
deliberate two-step workflow: the technician can't get the disposal site's signature or the
certificate photo until after they've actually been there and dumped the load, which is normally
after the job card itself is already complete.

To clear the flag:

1. Open the **History** tab and tap **Upload Disposal Certificate** on the flagged job card.
2. Fill in the disposal site's name, have them sign on screen, and attach a photo of the physical
   certificate handed over at the site.
3. Tap **Save Certificate** — this sends a second, separate email to the office with the disposal
   site signature and certificate photo attached, subject line
   `Safe Disposal Certificate — Job Card #<job no> - <client>`.
4. Once saved successfully, the job card's red flag clears and it shows "Certificate uploaded ✓".

The History tab shows Job Number, Date, Technician Name, Client Name, and Safe Disposal Required
(Yes/No) for every submitted job card, so it doubles as a quick way to see which jobs still need a
certificate uploaded.

## The Google review link

`GOOGLE_REVIEW_URL` in `config.json` is already set to a verified link straight to DC24's real
Google Business listing (confirmed: "Drain Clean 24", 71 Industria Ring Rd, Parow Industrial, 4.9★
from 166 reviews) — tapping it opens the listing, where the client can tap "Write a review" or the
star rating directly.

If you'd like the smoother one-tap version (opens the star-rating dialog immediately, no extra
tap), Google Business Profile has a "Get more reviews" feature that generates a short link like
`g.page/r/xxxxxxxxxxxx/review` — only the account owner can generate this (Business Profile
dashboard → Get more reviews → Copy link). If you grab that, just swap it into `GOOGLE_REVIEW_URL`
in `config.json` and restart the server — no other changes needed.

## Going live (beyond your office wifi)

Right now this runs on one computer and is only reachable on the same wifi network. For
technicians out in the field on mobile data, `server.py` needs to run somewhere with a public
address. The easiest free options are Render or Railway — both can run this app at no cost for
low traffic, with no server admin required.

**Every setting normally kept in `config.json` (including your SMTP password) can instead be set
as an environment variable in the hosting platform's own dashboard.** This is the recommended way
to host it — you never need to commit `config.json` or any password to a repository at all. The
environment variable names are exactly the same as the keys in `config.example.json`
(`SMTP_HOST`, `SMTP_PORT`, `SMTP_USE_TLS`, `SMTP_USE_SSL`, `SMTP_USER`, `SMTP_PASSWORD`,
`EMAIL_FROM`, `EMAIL_TO`, `COMPANY_NAME`, `START_JOBNO`, `GOOGLE_REVIEW_URL`).

### Deploying to Render (recommended)

1. Push this folder to a new GitHub repository (or use Render's "Public Git Repository" option if
   you'd rather not use GitHub — ask your developer if you're unsure how to do this part).
2. On [render.com](https://render.com), sign up/log in, then **New +** → **Web Service** → connect
   the repository.
3. Render should auto-detect it as a Python app. Leave **Build Command** blank (or `true` — no
   packages need installing) and set **Start Command** to `python3 server.py`.
4. Under **Environment**, add each of the variables listed above with your real SMTP details —
   this is the one place your password gets typed in, and it stays inside Render's dashboard.
5. Deploy. Render gives you a public URL like `https://dc24-job-card.onrender.com` — that's what
   goes into the CRM's Job Card button, and what technicians open on their phones.

A `render.yaml` file is included in this project so Render can pick up steps 3-4 automatically as
a "Blueprint" if you use that option instead of the manual New Web Service flow.

**Two things to know about Render's free tier:** a free service "spins down" after periods of no
traffic and takes up to a minute to wake up on the next request — the technician just needs to
wait for the page to load on the first open of the day. Also, the free tier's disk is temporary —
if the service restarts, `sequence.json` (which tracks the next job number) resets. If job numbers
matter to you precisely, either upgrade to a paid instance with a persistent disk, or set
`START_JOBNO` again after any long gap in use.

### Deploying to Railway (alternative)

Much the same idea: create a project at [railway.app](https://railway.app), connect this repo (or
run `railway up` from this folder with Railway's CLI), set the same environment variables under
the project's **Variables** tab, and Railway will detect the included `Procfile`
(`web: python3 server.py`) automatically. Railway also assigns a public URL once deployed. The
same free-tier caveats about sleep/wake and disk persistence generally apply.

### Other options

- **Small cloud VM** (a R100-200/month DigitalOcean/Linode droplet, or similar) — copy these files
  across, install Python (already standard on Linux), run `server.py` behind a process manager
  (e.g. `systemd`) so it restarts automatically. Here you'd still use a real `config.json` since
  there's no platform dashboard for environment variables — just don't share that file.
- **Alongside your existing Leakfind hosting**, if your developer has server access there already.

## What was verified before handing this off

This wasn't just written and assumed to work — it was tested end-to-end: a local test mail server
was stood up, a full test job card (with a description, materials list, a photo, and a signature)
was submitted through the real HTTP form-submission code path, and the resulting email was
inspected directly. The subject line, all job details, the materials table, and both the signature
and photo attachments all arrived correctly formatted.

## Fields captured on each job card

- Job No. (auto-assigned), Planon Number, customer name, site, address, contact person, telephone,
  email, billing information
- Job Description details
- Job Type, Drain Type, Liquid Waste, Pump Out Internal Fattraps, Pump External Tank (+ specify),
  Consumables (Degreaser/Disinfectant/Acid with litres, Microbes, Beads), Waste Stream (+ other),
  Waste Type — all as tap-to-select chips, matching the paper form's checkboxes
- Quote Requirements
- Materials/parts used (add as many lines as needed)
- Before photos and After photos, captured separately (compressed automatically so emails stay a
  reasonable size)
- Two sign-offs on the main card: Customer and Driver — each with a printed name and on-screen
  signature
- A Yes/No answer to "Is this job card linked to a disposal site certificate?"
- Comments and a Poor/Fair/Good/Excellent service rating
- Date, plus two Time In/Time Out slots for jobs with a return visit the same day
- If Yes was selected above: a follow-up Disposal Site sign-off (name + signature) and a photo of
  the physical certificate, captured later from the History tab (see "Safe disposal certificate
  follow-up" above)

## Limitations to know about

- There's no login/authentication on the form itself — anyone with the link can submit a job card.
  If that matters, ask your developer to add a simple shared PIN or per-technician login before
  going live company-wide.
- Local job card history lives only on that one phone's browser storage — it's a personal
  "did this send OK" log, not a shared company database. The email itself is the permanent record.
- Very large photo sets could make an email slow to send on a poor mobile connection — photos are
  compressed automatically, but keeping it to a handful of the most useful shots per job is best
  practice.
