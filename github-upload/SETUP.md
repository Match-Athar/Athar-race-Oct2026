# Put athar-race-new on automatic updates (one time, ~10 minutes)

Signed in as **ibraq-athar**, in the repository **athar-race-new**. Do NOT upload this SETUP.md.

## 1. Upload the code
1. **Add file → Upload files**.
2. Open the folder `github-upload\athar-race-new` on your PC and drag **everything inside it** onto the page:
   `athar`, `templates`, `run.py`, `requirements.txt`, `README.md`, `.gitignore` (and `.github` if it lets you).
3. **Commit changes**.
4. If the `.github` folder did not go up (check the file list for `.github`):
   **Add file → Create new file**, type the name `.github/workflows/update-board.yml`,
   paste the whole content of `github-upload\athar-race-new\.github\workflows\update-board.yml`, **Commit changes**.

## 2. Add the three secrets
**Settings → Secrets and variables → Actions → New repository secret**, three times:

| Name | Value |
|---|---|
| `ODOO_API_URL` | `https://ibraqperfumes.odoo.com/api/bi/v1/pos/sales/detail` |
| `ODOO_API_TOKEN` | the live API token (the `ODOO_API_TOKEN=` value in your `.env`) |
| `TARGET_XLSX_B64` | the target file as text — see below |

For `TARGET_XLSX_B64`: in the `athar-dashboard` folder run **one** of these

    Git Bash:    base64 -w0 data/target.xlsx | clip
    PowerShell:  [Convert]::ToBase64String([IO.File]::ReadAllBytes("data\target.xlsx")) | Set-Clipboard

then paste (Ctrl+V) into the secret's value box. Nothing is saved on your PC.

## 3. Switch Pages to GitHub Actions
**Settings → Pages → Build and deployment → Source: GitHub Actions**.

## 4. First run
**Actions** tab → **Update Athar race board** → **Run workflow**. The first run takes about 3–4 minutes
(it downloads the whole month); after that each run takes about 1 minute and starts by itself about every
10 minutes. Board: https://ibraq-athar.github.io/athar-race-new/

## Every month
Replace the `TARGET_XLSX_B64` secret with the new month's target file (same PowerShell command).

## Good to know
- GitHub starts scheduled runs a few minutes late at busy times, so expect updates every 10–20 minutes.
- GitHub pauses scheduled runs in a public repository after **60 days without a commit**. If that happens,
  the Actions tab shows a button to turn it back on.
- If the API token changes, update `ODOO_API_TOKEN`; the first run after that downloads the month again.
- Run logs are public: they only say "Board built at …". If a run fails, the log shows the error message
  (never amounts).
