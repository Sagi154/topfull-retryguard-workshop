# Coordinate with mentors (before Phase 1)

Ask your mentors these **before** you create cloud VMs (Phase 1). One short meeting or message thread is enough.

Related: [PREREQUISITES.md](PREREQUISITES.md) | [SETUP-GUIDE.md](SETUP-GUIDE.md) Phase 0 | workplan canvas (`canvases/topfull-retryguard-workplan.canvas.tsx`)

---

## Checklist

- [ ] **Cloud credits** - Lab subscription, shared account, or pay yourself?
- [ ] **Cloud provider** - Azure (TopFull default), AWS, or GCP?
- [ ] **VM budget & timeline** - How many days can VMs run? (~4 VMs, ~$5-15/day while on)
- [ ] **RetryGuard integration point** - Where should retries be turned on/off? (TopFull proxy, Istio, app config, etc.)
- [ ] **Report expectations** - Required plots/metrics? (goodput, latency, retries/request, cost, comparison table format)

---

## Notes

**RetryGuard code:** You implement Algorithm 1 from `RetryGuard.pdf` - mentors do not need to give you source. You **do** need a clear answer on **where** in the stack your controller disables/enables retries.

**Baseline vs experiment:** Confirm both runs use the same Locust scenario; only retry policy changes (Phase 5 baseline -> Phase 6 RetryGuard).

**Out of scope unless mentors say otherwise:** DAGOR, DiffTry, extra overload-control baselines.

---

## Suggested message to mentors

> We're starting Project 1 (TopFull + self-implemented RetryGuard on K8s / Online Boutique). Before we provision VMs: do we have lab cloud credits and a preferred provider? Where should RetryGuard hook retries (proxy vs mesh vs app)? What should the final report include? We'll implement RetryGuard from the paper, not from provided code.
