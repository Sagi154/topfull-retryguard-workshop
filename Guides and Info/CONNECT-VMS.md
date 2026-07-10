# Agent playbook: SSH into TopFull GCP VMs

**Audience:** Cursor agents setting up SSH for a teammate on Windows so they can run `ssh topfull-master` (and worker/load) without a password.

**Trigger:** User asks to connect to the workshop VMs, fix SSH, set up `~/.ssh/config`, or similar.

**Shared GCP project:** `networks-workshop`  
**Zone:** `us-central1-a`  
**VMs:** `topfull-master`, `topfull-worker-1`, `topfull-load`

Related human docs: [SETUP-GUIDE.md](SETUP-GUIDE.md) | [PREREQUISITES.md](PREREQUISITES.md)

---

## Agent rules (read first)

1. **Do the work yourself** with the Shell tool. Do not only paste instructions unless blocked on interactive login.
2. **Discover values on this machine** — do not copy another teammate’s `User`, `HostName`, or `IdentityFile` from examples in chat history.
3. **`User` is never an email.** It is the Linux account on the VM (usually the Windows username, e.g. `sagi1`). Browser SSH may show a different user (e.g. `sagi151ps`); ignore that for local OpenSSH.
4. **Stopped VMs have no public IP.** `Connection timed out` almost always means `TERMINATED` or stale `HostName`, not a missing firewall rule. Project already has `default-allow-ssh` (`tcp:22` / `0.0.0.0/0`).
5. **Ephemeral IPs change on stop/start.** After every start, refresh `HostName` in `~/.ssh/config`.
6. **Interactive blockers:** `gcloud auth login` and first-time `ssh-keygen` passphrase prompts need the human. Stop, tell them what to complete, then continue.
7. **Do not** commit private keys, `.pub` contents into git secrets carelessly, or overwrite unrelated `Host` blocks in `~/.ssh/config`.
8. **Success criteria:** all three of these exit 0 with no password prompt:
   ```powershell
   ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami"
   ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "hostname; whoami"
   ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "hostname; whoami"
   ```

---

## Procedure

### Step 0 — Detect local identity

Run:

```powershell
whoami
echo $env:USERNAME
echo $env:USERPROFILE
Test-Path "$env:USERPROFILE\.ssh\id_ed25519"
Test-Path "$env:USERPROFILE\.ssh\id_ed25519.pub"
gcloud version
gcloud auth list
gcloud config get-value project
```

Record:

| Variable | How to get it |
|----------|----------------|
| `WIN_USER` | `$env:USERNAME` (typical SSH `User`) |
| `USERPROFILE` | `$env:USERPROFILE` |
| `KEY` | `$env:USERPROFILE\.ssh\id_ed25519` |
| `PUB` | `$env:USERPROFILE\.ssh\id_ed25519.pub` |

---

### Step 1 — Ensure SSH key exists

If `id_ed25519` is missing:

```powershell
ssh-keygen -t ed25519 -f "$env:USERPROFILE\.ssh\id_ed25519" -C "workshop-topfull" -N '""'
```

If `ssh-keygen` refuses empty passphrase non-interactively, ask the user to run keygen once, then continue.

Read the public key (needed in Step 4):

```powershell
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub"
```

---

### Step 2 — Ensure `gcloud` can see the VMs

```powershell
gcloud config set project networks-workshop
gcloud compute instances list --format="table(name,zone,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

**If permission error or empty/wrong project:**

1. Check `gcloud auth list`. The active account must be a member of `networks-workshop` (often a personal Gmail, not a university account).
2. If the right account is missing, run `gcloud auth login` and **ask the user to finish the browser flow**, then:
   ```powershell
   gcloud config set account CORRECT_EMAIL
   gcloud config set project networks-workshop
   ```
3. Re-list instances. Proceed only when all three `topfull-*` VMs appear.

---

### Step 3 — Start VMs and capture public IPs

```powershell
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a

gcloud compute instances list `
  --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Require `STATUS=RUNNING` and a non-empty `NAT_IP` for each. Store:

- `IP_MASTER`
- `IP_WORKER`
- `IP_LOAD`

Optional reachability check:

```powershell
Test-NetConnection $IP_MASTER -Port 22
```

`TcpTestSucceeded : True` expected once the VM is up. Ping may fail on GCP — ignore ping.

---

### Step 4 — Install this machine’s public key on each VM

Use `gcloud compute ssh` (creates the local Linux user matching this PC and writes `authorized_keys`). Prefer this over browser SSH.

```powershell
$pub = (Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" -Raw).Trim()
$remote = @"
mkdir -p ~/.ssh && chmod 700 ~/.ssh
touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys
grep -qxF '$pub' ~/.ssh/authorized_keys || echo '$pub' >> ~/.ssh/authorized_keys
hostname; whoami
"@

foreach ($vm in @('topfull-master','topfull-worker-1','topfull-load')) {
  Write-Host "=== $vm ==="
  gcloud compute ssh $vm --zone=us-central1-a --command=$remote --quiet
}
```

From the `whoami` line, set `SSH_USER` (must match across VMs; typically equals `WIN_USER`).

**Notes for agents:**

- First run may generate a gcloud SSH key and update project metadata — allow it.
- Host-key prompts: prefer OpenSSH with `StrictHostKeyChecking=accept-new` in config; if `gcloud` uses Plink and hangs on “Store key in cache?”, ask the user to accept once, or retry.
- Do **not** assume `SSH_USER` is `sagi151ps` or any browser-SSH username.

---

### Step 5 — Write / update `~/.ssh/config`

Path: `$env:USERPROFILE\.ssh\config`

- If the file exists, **update or insert** only the three `Host topfull-*` blocks. Leave other hosts untouched.
- Use discovered `IP_*`, `SSH_USER`, and this machine’s `IdentityFile`.

Template (substitute real values):

```
Host topfull-master
  HostName <IP_MASTER>
  User <SSH_USER>
  IdentityFile <USERPROFILE>\.ssh\id_ed25519
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new

Host topfull-worker-1
  HostName <IP_WORKER>
  User <SSH_USER>
  IdentityFile <USERPROFILE>\.ssh\id_ed25519
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new

Host topfull-load
  HostName <IP_LOAD>
  User <SSH_USER>
  IdentityFile <USERPROFILE>\.ssh\id_ed25519
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
```

On Windows, `IdentityFile` may be `C:\Users\<WIN_USER>\.ssh\id_ed25519`.

---

### Step 6 — Verify (required)

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-master "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-worker-1 "hostname; whoami"
ssh -o BatchMode=yes -o ConnectTimeout=8 topfull-load "hostname; whoami"
```

`BatchMode=yes` fails fast instead of prompting for a password — treat a password prompt / non-zero exit as failure and go to Troubleshooting.

Report to the user: aliases work, usernames, and current public IPs. Remind them IPs change after stop/start.

---

## Reconnect after VMs were stopped (short path)

When the user already completed setup once:

```powershell
gcloud config set project networks-workshop
gcloud compute instances start topfull-master topfull-worker-1 topfull-load --zone=us-central1-a
gcloud compute instances list --format="table(name,status,networkInterfaces[0].accessConfigs[0].natIP)"
```

Update the three `HostName` lines in `~/.ssh/config`, then re-run Step 6 verify.

If verify fails with auth error, re-run Step 4 (key may be missing for this user on a rebuilt VM).

---

## Stop VMs (when user asks to save cost)

```powershell
gcloud compute instances stop topfull-master topfull-worker-1 topfull-load --zone=us-central1-a
```

Do **not** stop VMs unless the user asks.

---

## Troubleshooting (agent decision table)

| Observation | Action |
|-------------|--------|
| `Connection timed out` / `TcpTestSucceeded : False` | List instances; if `TERMINATED` or empty `NAT_IP` → start; if IP ≠ config → fix `HostName` |
| Permission denied / BatchMode fails | Wrong `User` or missing key → re-run Step 4; set `User` to `whoami` from that step |
| `gcloud` cannot list `networks-workshop` | Wrong account → user must `gcloud auth login` with project member email |
| Browser SSH works, local SSH fails | Different Linux users — install key via Step 4 for **this PC’s** user, not browser user |
| Gaia / Regional Access Boundary warnings | Ignore if API calls still succeed |
| Need more detail | `ssh -v topfull-master` → look for `Authentication succeeded (publickey)` |

---

## Out of scope for this playbook

- Creating/deleting VMs or changing firewall unless list/start proves a real network block (unlikely in this project)
- Using university `gcloud` accounts that lack `networks-workshop` IAM
- Committing `~/.ssh` private keys into the repo
