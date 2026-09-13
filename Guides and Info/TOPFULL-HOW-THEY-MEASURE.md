# How TopFull measures whether it is working well

Plain-language notes from the TopFull paper (`context/TopFull.pdf`).
This is about **how the paper scores TopFull**, not about RetryGuard.

If a short form appears later in this file, the first time it is used it is written out in full.

---

## The one-sentence version

TopFull is doing a good job when **more user requests finish successfully, and fast enough** — even when the system is overloaded.

That number is called **goodput**. Almost every chart in the paper is some form of goodput.

---

## Words you will see

| Term | What it means in everyday language |
|---|---|
| **Request** | One user action, like “show me this product” or “check out my cart”. |
| **API** (Application Programming Interface) | A named type of request the shop exposes. In Online Boutique the five APIs they test are: checkout, get product, get cart, add to cart, empty cart. |
| **Microservice** | One small program that does one job (cart, payment, product catalog, …). A single user request often visits several of them in a chain. |
| **Overload** | More requests arrive than the services can handle. Queues grow, answers get slow, some requests fail. |
| **Throttle / rate limit** | Intentionally **reject some requests at the front door** so the services behind it do not collapse. TopFull does this at **entry** (the frontend), not inside every service. |
| **SLO** (Service Level Objective) | A promise about quality. Here: “a successful answer should come back in **at most 1 second**.” If it takes longer, it **misses the SLO**, even if it eventually succeeds. |
| **Latency** | How long one request takes, in milliseconds (ms). 1000 ms = 1 second. |
| **Percentile latency (P95)** | Sort all request times. P95 is the time that 95% of requests were *faster than*. It describes the slow tail, not the average. |
| **Throughput / RPS** (requests per second) | How many requests the system **tries** to handle each second. This counts fast ones, slow ones, and failures together. |
| **Goodput** | How many requests **succeed and meet the SLO** each second. This is the useful work. |
| **Success rate** | Of the requests users sent, what percent actually succeeded. |
| **Starvation** | A service wastes time on a request that will be dropped later in the chain. Meanwhile another request that *could* have finished is squeezed out. |
| **vCPU** | A virtual CPU core the cloud gives a machine. “Fewer vCPUs for the same goodput” means cheaper. |
| **Autoscaler** | Kubernetes (k8s) adding extra copies of a service when load rises. That takes seconds to minutes, so overload can still happen in the meantime. |
| **RL** (Reinforcement Learning) | A program that learns by trial and error: try an action, see if goodput went up, repeat. TopFull uses RL to decide *how hard* to throttle. |
| **DAGOR / Breakwater** | Two older overload-control systems TopFull compares itself against. You do not need their internals to read the scores. |

---

## 1. What they are trying to maximize

Imagine a shop with a door (the frontend) and rooms behind it (cart, checkout, catalog, …).

If too many people enter, workers in the rooms get stuck:

- some customers wait too long (SLO miss)
- some get an error
- some get halfway through checkout and then fail — wasted work

TopFull’s goal:

> Choose, for each type of request, **how many to let in per second**, so that the **total number of finished, on-time answers is as high as possible**, without overloading the rooms.

They write this as: maximize \(G(x_1, \ldots, x_n)\).

- \(G\) = total goodput (good answers within the SLO)
- \(x_i\) = how many of API *i* they allow in (the rate limit)

They only turn the knob at the **front door**, not in every room.

---

## 2. Goodput — the main efficiency number

**Throughput** = “we touched this many requests.”  
**Goodput** = “this many customers actually got a useful, on-time answer.”

In the paper, a request counts toward goodput only if **both** are true:

1. It **succeeded** (no error).
2. It finished in **1 second or less** (their SLO).

A slow success does **not** count. A failure does **not** count. Work that was started and then dropped later does **not** count.

**Example.** 1000 requests arrive in one second.

- 700 finish OK in under 1 second → goodput = **700 rps**
- 200 finish OK but take 3 seconds → not goodput
- 100 fail → not goodput

That is why they talk about “1.82× DAGOR”: under the same overload, TopFull produced about **1.82 times as many on-time successes per second**.

They also plot **success rate (%)**: of everything users asked for, how many succeeded. Once the shop is full, a good controller’s goodput and success rate should **stay flat**, not crash as even more people arrive.

---

## 3. How they collect that number

- Load is generated with **Locust** (a tool that pretends to be many shoppers).
- They look at **end-to-end** time: from the user hitting the frontend until the full answer is back. Not the time inside one microservice.
- For Online Boutique they report five APIs separately **and** the total:
  - `postcheckout` — place an order
  - `getproduct` — view a product
  - `getcart` / `postcart` / `emptycart` — cart actions

Per-API charts answer: “did we save checkout by starving ‘get product’?” Total charts answer: “did the whole shop serve more useful work?”

CPU use is **not** the score. They use CPU only as a **warning light** (“this service is probably overloaded,” in one analysis when CPU is above 80%). High CPU with low goodput is failure, not efficiency.

---

## 4. Other numbers they use (still in service of goodput)

These are supporting pictures, not a second scoring system.

### Speed of recovery (convergence)

After overload starts, **how many seconds until goodput climbs to its best stable level?**

- TopFull: about **5 seconds**
- DAGOR with a small step: about **27 seconds**
- DAGOR with a huge step: never settles (too jumpy)

Faster recovery means fewer wasted seconds of bad service.

### Cost (goodput vs cores)

They ask: “If I give the bottleneck fewer **vCPUs**, can TopFull still keep goodput up?”

Result they advertise: **same or better goodput with 50–57% fewer vCPUs** during short traffic spikes. That is cost efficiency: more useful answers per core.

### Together with the autoscaler

Kubernetes can add pods, but slowly. During the wait, TopFull throttles at the door so the existing pods do not die.

They report **1.38× to 3.91× more average goodput** during a traffic surge than the autoscaler running alone, using the **same** amount of CPU.

### Starvation check (per-API goodput over time)

If total goodput looks fine but one API is near zero, the controller is being unfair (or wasteful). They plot each API over time to show TopFull does not kill one API to feed another when both could have been served.

---

## 5. How the RL controller itself “sees” efficiency

Every **1 second**, for the APIs it is currently controlling, it looks at two things:

1. **Goodput ÷ current rate limit** — of the requests we *allowed in*, how many were actually good? If this is low, we are letting in too many.
2. **The worst (highest) percentile latency** among those APIs — are we missing the SLO?

Then it multiplies the rate limit by a factor between **0.5** (cut admitted traffic a lot) and **1.5** (let more in).

It learns from a **reward**:

> reward = (change in goodput) minus a penalty if latency is worse than the SLO

In words: **more on-time successes = good**. **Breaking the 1-second promise = bad**. No CPU term in the reward.

They train this first on a fake graph (**simulator**), then fine-tune on the real app. That training trick is called **Sim2real** (simulate-to-real). It is about making training cheaper, not about scoring a live experiment.

---

## 6. Headline results (so you know what “efficient” looked like for them)

Compared with other overload controllers, **under overload**:

- **1.82×** the average goodput of DAGOR
- **2.26×** the average goodput of Breakwater

Compared with Kubernetes autoscaling **alone**, during a traffic surge:

- up to **3.91×** more goodput (Online Boutique)
- **1.38×** more goodput (Train Ticket, another demo shop)
- same goodput with up to **57% fewer** vCPUs on short spikes

They also show that turning off pieces of TopFull (no clustering, or a dumb “always multiply by a fixed number” controller instead of RL) **lowers** goodput. That is how they argue each piece is worth it.

---

## 7. How this maps to *our* experiment files

Our runner writes one CSV per API, one row per second, with columns:

`RPS, Fail, Goodput, Latency95, Latency99`

| Column | Close to the paper? |
|---|---|
| **RPS** | Offered / observed request rate (throughput). Not the score. |
| **Fail** | Errors per second. |
| **Goodput** | In our collector this is `RPS − Fail` (HTTP success). The **paper** also requires latency ≤ 1 second. So our CSV goodput can look a bit **more optimistic** than the paper if many successes are slow. |
| **Latency95** | End-to-end P95. Use this to see SLO pain. The paper’s SLO is **1 second (1000 ms)**. |
| **Latency99** | Not used in the paper’s main tables. In our pipeline it is unused / not reliable; we report P95. |

For a paper-style score on our data: count requests that **succeeded and were faster than 1 second**, then turn that into rps. P95 and fail/reject rate are the supporting plots.

A longer “where files live / how to pull them” guide is [METRICS-COLLECTION-GUIDE.md](METRICS-COLLECTION-GUIDE.md).

---

## 8. What they do *not* treat as the main score

- Raw CPU or memory (warning light, not the grade)
- P99 latency (they use a hard 1-second SLO, not “the slowest 1%”)
- How expensive it was to **train** the RL model (reported separately in dollars/hours)
- How many CPU cycles the controller itself uses (they show it is small, then move on)

If someone asks “is TopFull efficient?”, the paper’s answer is: **does goodput go up, stay up, and (when they care about money) stay up with fewer cores?**
