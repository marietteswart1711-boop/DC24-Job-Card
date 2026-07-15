[dc24_README.md](https://github.com/user-attachments/files/30041756/dc24_README.md)
# DC24 Job Card App

A phone-friendly job card matching your existing DC24 paper job card/safe disposal certificate:
technician fills in the job details, the client (plus driver and disposal site) sign on screen, and
the completed job card is emailed to your office automatically — no manual step, no app store install.

## What's included

- `public/index.html` — the job card form technicians use (works in any phone browser), laid out
  to match the paper DC24 job card: job number, customer details, Planon number, job description,
  Job Type / Drain Type / Liquid Waste / Pump Out / Consumables / Waste Stream / Waste Type
  checklists, quote requirements, before & after photos, Customer and Driver sign-off, a Yes/No
  safe disposal certificate question, comments, service rating, and date/time in-out (with a
  second visit slot)
- `server.py` — a small Python server that receives submitted job cards and emails everything via
  your real SMTP account (Gmail, Outlook/365, or your existing business mail server)
- `config.example.json` — template for your SMTP settings
- `assets/dc24_header.png` and `assets/dc24_footer.png` — the DC24 letterhead banner and footer
  (SnapScan + review QR codes) that appear at the top and bottom of every emailed job card

No external packages are required — everything runs on Python's standard library.

## Letterhead header/footer

Every emailed job card (both the office copy and the client's copy) now includes your letterhead
as part of the email body: the `assets/dc24_header.png` banner at the top, and the
`assets/dc24_footer.png` footer (SnapScan payment QR code, review QR code, and contact details) at
the bottom. These are inlined into the email itself — not sent as separate attachments to open.

If you ever want to update either image (e.g. a new logo, a new QR code), just replace the file at
`assets/dc24_header.png` or `assets/dc24_footer.png` with a same-named PNG and commit — no code
changes needed. If either file is missing, the job card email still sends fine, it just won't have
that banner.

## Job numbers

Job numbers are entered manually by the technician on the form, matching the number from your
paper book/sequence. The server does not assign, track, or reserve job numbers — the technician
types the job number directly into the "Job No." field before completing the card, and it's
included as-is in the emailed job card.

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

1. Technician enters the job number for this job card.
2. Technician fills in job details, description of work, and any materials used.
3. Optional: attach before/after photos from the phone camera.
4. Client and driver sign directly on the phone screen.
5. Technician answers **"Is this job card linked to a disposal site certificate?"** (Yes/No).
6. Tap **Complete Job Card** — the email sends immediately in the background to
   `info@drainclean24.co.za` (or whatever `EMAIL_TO` is set to). If the customer's email address
   was filled in and looks valid, they automatically get their own copy too (subject "Your Job
   Card #...") — sent in addition to, never instead of, the office copy. A missing or badly
   typed client email just skips that copy quietly; it never blocks the job card itself from
   going through.
7. A thank-you screen appears with a **⭐ Rate DC24 on Google** button — handy to hand the phone to
   the client right there on site while the job is fresh. Tapping **Start Next Job Card** dismisses
   it and clears the form, ready for the next job number to be entered.
8. If there's no signal at the moment of submission, the job card is saved in the phone's local
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
2. Fill in the disposal site's name, have them sign on screen, and attach the certificate as a
   **PDF** (this upload is PDF-only — a scanned or emailed copy of the certificate, not a photo).
3. Tap **Save Certificate** — this sends a second, separate email to the office with the disposal
   site signature and the certificate PDF attached, subject line
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
`EMAIL_FROM`, `EMAIL_TO`, `COMPANY_NAME`, `GOOGLE_REVIEW_URL`).

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

**One thing to know about Render's free tier:** a free service "spins down" after periods of no
traffic and takes up to a minute to wake up on the next request — the technician just needs to
wait for the page to load on the first open of the day.

### Deploying to Railway (alternative)

Much the same idea: create a project at [railway.app](https://railway.app), connect this repo (or
run `railway up` from this folder with Railway's CLI), set the same environment variables under
the project's **Variables** tab, and Railway will detect the included `Procfile`
(`web: python3 server.py`) automatically. Railway also assigns a public URL once deployed. The
same free-tier caveats about sleep/wake generally apply.

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

## Vehicle field

Each job card has a Vehicle dropdown: Gigantor LW11, Big Foot LW10, Isuzu LW9, Biggie Smalls,
Dyna LW8, DYNA 2.0, or OTHER. Selecting OTHER reveals a free-text field so the technician can type
in a vehicle name that isn't on the list. The vehicle appears on the emailed job card and in the
Excel export.

## Dumping Site field

Each job card has a Dumping Site dropdown: Borcherds Quarry, Okran, Drakenstein, Fuel44, Biogas,
Nun2Waste, or Other. Selecting Other reveals a free-text field for a dumping site that isn't on the
list. This is separate from the Safe Disposal Certificate follow-up (which records the disposal
site's own signature and a certificate photo after the load is dumped) — Dumping Site is just a
quick record of where the load was taken, filled in on the main job card itself. It appears on the
emailed job card and in the Excel export.

## Downloading job card history to Excel

On the **History** tab, tap **⬇ Download to Excel** to export the currently filtered list of job
cards (Job No., date-range, and technician filters all apply to the export too — clear the filters
first if you want everything) to a real `.xlsx` file, downloaded straight to the phone/device. The
export includes every field on the job card — customer details, job description, all the
checklists, materials, vehicle, comments, rating, times, and disposal certificate status — except
for signatures and photos, which don't translate to a spreadsheet. This works fully offline/on-device
(no server round-trip) using the SheetJS library loaded from its CDN.

## Fields captured on each job card

- Job No. (entered manually by the technician), Vehicle, Dumping Site, Planon Number, customer
  name, site, address, contact person, telephone, email, billing information
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
- If Yes was selected above: a follow-up Disposal Site sign-off (name + signature) and the
  certificate itself as a PDF upload, captured later from the History tab (see "Safe disposal
  certificate follow-up" above)

## Limitations to know about

- There's no login/authentication on the form itself — anyone with the link can submit a job card.
  If that matters, ask your developer to add a simple shared PIN or per-technician login before
  going live company-wide.
- There's no validation that a job number hasn't already been used or is in the right sequence —
  since it's entered manually, it's on the technician to enter the correct number from your paper
  book/sequence.
- Local job card history lives only on that one phone's browser storage — it's a personal
  "did this send OK" log, not a shared company database. The email itself is the permanent record.
- Very large photo sets could make an email slow to send on a poor mobile connection — photos are
  compressed automatically, but keeping it to a handful of the most useful shots per job is best
  practice.
