# Splendor — Business Model & GPL Memo (v0.1, draft)

> Resolves the open monetization question [D-1.4] by first pinning down what the GPL actually forbids and
> permits, then mapping where Splendor can legally capture value, then modeling concrete revenue models
> against the Citrate stack. Ends with a recommendation and the decisions this asks of you.
>
> **This is not legal advice.** I am not a lawyer. Every "GPL-safe" call here is an engineering-informed
> reading that must be confirmed by IP counsel before you rely on it; the token/custody sections need
> securities + money-transmission counsel specifically. Flagged inline as ⚖️.

---

## 0. TL;DR
- **You cannot make the Splendor app proprietary, and you cannot bolt closed-source paid features into the
  distributed binary.** GPL forces the whole distributed app open. Accept this; it's Blender's own model.
- **You *can* capture enormous value, because GPL copyleft is triggered by _distribution_, not by _hosting_.**
  Anything that runs behind a network API — cloud inference, managed training, hosted eval, the gallery,
  pinning, chain deploy — can be a paid service, and its *server* code need not be GPL (plain GPL has no
  network-copyleft; that's AGPL, which Blender is not).
- **Your real moat is not code secrecy — it's the trademark, the official builds, the hosted network, and
  the Citrate protocol economics.** This is the Red Hat / Blender / Automattic playbook, plus a crypto-native
  revenue layer almost no creative tool has.
- **Recommended model:** *Open GPL app (free) + proprietary Citrate-connected services + protocol take-rate*,
  with a foundation-style stewardship shell at v1. Details in §5–6.

---

## 1. The GPL reality (precise)
Blender — and therefore Splendor — is **GNU GPL v2-or-later** (GPLv3-compatible). The load-bearing facts:

### 1.1 Distribution triggers copyleft; hosting does not
- If you **distribute** the Splendor binary (downloads, Steam, itch, installers) [D-8.8], you must make the
  **complete corresponding source** available under GPL. → The desktop app is open, full stop.
- If you **run** Splendor (or modified Splendor) **on a server to provide a service over a network**, plain
  GPL imposes **no obligation to release that server's source.** This is the so-called SaaS/ASP gap that
  AGPL exists to close — and Blender is *not* AGPL. **This is your primary value-capture lever.** ⚖️

### 1.2 What counts as a derivative (and must be GPL if distributed)
- **Add-ons / scripts that `import bpy`** and are shipped as part of Splendor are treated by the Blender
  Foundation (and FSF) as **derivative → must be GPL-compatible.** So Splendor's in-app Python layer,
  retro nodes, in-app agent, and in-process MCP server are all **GPL**. Plan for it — it's fine.
- **Separate programs at arm's length** — a distinct process communicating over a general-purpose,
  documented protocol (e.g. an external service Splendor calls over MCP/HTTP/socket) — are **arguably not
  derivative** and may carry a different license. This is legally grey and fact-specific; keep any code you
  want non-GPL in a genuinely separate service with a clean, general interface, and get it blessed. ⚖️
- **User-created assets** (`.blend` files, exported glTF/USDZ, renders, minted works) are **not** derivative
  of Splendor. Creators fully own their output — critical for the on-chain/marketplace story.

### 1.3 What GPL forbids for monetization
- ❌ A closed-source Splendor core.
- ❌ "Open-core" in the naive sense of *free binary + paid closed-source features inside the same app.* If a
  feature is compiled/shipped in the distributed app, it's GPL. Paid features must instead be **hosted
  services the open app calls**, gated by account/license — not closed code in the binary.
- ❌ Relicensing Blender's code (you can't slap AGPL or a proprietary license on the inherited code).

### 1.4 What GPL explicitly permits
- ✅ **Selling** the software (GPL is about freedom, not price) — though recipients may redistribute freely,
  so paid binaries alone are a weak moat.
- ✅ **Proprietary independent services** behind a network boundary (§1.1).
- ✅ **Trademark control** — the GPL covers copyright, not your marks. You can give the code away and still
  own "Splendor," the logo, the domain, and the right to call something an *official* build. **This is the
  enforceable moat.**
- ✅ **Dual-licensing code _you_ author** (not the inherited Blender code) however you like — including AGPL
  to protect your own server components (§7.3).

---

## 2. The value map — three zones
```
 ┌────────────────────────────────────────────────────────────────────────┐
 │ ZONE A — THE APP (GPL, free, open)                                       │
 │  Splendor desktop: retro engine, in-app agent, MCP server, node/edge     │
 │  language, DSL, bundled Eval SDK. Everything distributed = GPL.          │
 │  Value role: adoption engine + brand + community. NOT a direct revenue.  │
 ├────────────────────────────────────────────────────────────────────────┤
 │ ZONE B — NETWORK SERVICES (your license choice; hosting, not distributed)│
 │  Cloud inference, managed LoRA/model training, Eval-as-a-Service,        │
 │  hosted gallery + embeddable player, storage/pinning, render farm,       │
 │  team/collab backend, model registry. → paid, closed-source-OK.          │
 ├────────────────────────────────────────────────────────────────────────┤
 │ ZONE C — CITRATE PROTOCOL (on-chain economics)                           │
 │  DePIN compute marketplace take-rate, mint/primary-sale fees, secondary  │
 │  royalties, licensing registry fees, pinning fees, attestation/notary.   │
 │  → protocol-native revenue, uniquely yours.                              │
 └────────────────────────────────────────────────────────────────────────┘
```
**Rule of thumb:** if it ships in the app, it's GPL and free. If it lives behind the network or on the chain,
you can charge for it and keep the server code closed. Design the product so the paid value naturally lives
in Zones B and C.

---

## 3. Revenue streams (enumerated, rated)
Legend — **GPL-safe**: ✅ clean / 🟡 grey, needs counsel / ⚖️ regulatory. **Moat**: strength of defensibility.

| # | Stream | Zone | GPL-safe | Moat | Effort | Notes |
|---|--------|------|----------|------|--------|-------|
| 1 | Managed cloud **inference** (frontier + hosted local) | B | ✅ | Med | Med | Local-first app makes this pure opt-in upgrade for hard tasks. |
| 2 | Managed **model/LoRA training** (diffusion/LLM/3D) | B | ✅ | Med-High | High | Ties to [D-3.1/3.2]; the "train your retro style" hook. |
| 3 | **Eval-as-a-Service** / benchmarking cloud | B | ✅ | **High** | Med | The eval pillar [D-3.3] as a paid API + leaderboard; few competitors have this. SDK is open; the hosted grading/regression backend is closed. |
| 4 | **Hosted gallery** + embeddable player + creator pages | B | ✅ | High (network effect) | Med | Community flywheel; freemium (free public, paid private/pro/analytics). |
| 5 | **Storage / pinning** (Citrate pinning resale) | B/C | ✅ | Med | Low | Margin on pinned assets; bundles with mint. |
| 6 | Cloud **render farm** (retro render at scale) | B | ✅ | Med | Med | Classic Blender-adjacent revenue; retro presets as the differentiator. |
| 7 | **Team/collab** backend (shared projects, versioning, HIC audit) | B | ✅ | Med-High | Med | The B2B/studio upsell; HIC audit trail is a governance selling point. |
| 8 | DePIN **compute marketplace take-rate** | C | ✅ | **High** | High | % of compute sourced through CitrateNetwork [D-3.2]; scales with usage, not seats. |
| 9 | **Mint / primary-sale** fee | C | 🟡⚖️ | Med | Low | Small % on works minted through Splendor. |
| 10 | **Secondary royalty** enforcement | C | 🟡⚖️ | Med | Med | On-chain royalty split infra; creator-aligned. |
| 11 | **Licensing registry** fees (asset marketplace) | C | 🟡⚖️ | High | High | Game-asset marketplace with on-chain licenses/royalties [D-5.1]. |
| 12 | **Provenance/attestation** notary | C | ✅ | Low | Low | Likely a *free* adoption driver (attest work + eval scores); monetize adjacent. |
| 13 | Paid **official builds / auto-update / Steam** convenience | A | ✅ | Low | Low | GPL lets you sell; weak moat but frictionless for the Steam/itch audience [D-8.8]. |
| 14 | **Support / training / bounties / sponsorship** | A | ✅ | Low | Low | Foundation-style baseline; predictable but small. |
| 15 | **Utility token** (network/compute credits) | C | ⚖️⚖️ | — | High | See §7 — **do not** proceed without securities counsel. |

---

## 4. Business-model archetypes
| Archetype | What it is | Pros | Cons | Fit |
|-----------|------------|------|------|-----|
| **A. Open app + services** | Free GPL app; revenue from Zone-B services (inference/training/eval/gallery/render/teams). | GPL-clean, scalable, recurring, SaaS-margins. | Requires infra + ops; competitors can host too (mitigate via §7.3). | **Strong** |
| **B. Paid binary + support** | Sell official builds + support; source still open. | Simple. | Redistribution is free by GPL → leaky; low ceiling. | Weak alone; fine as stream #13/14. |
| **C. Foundation / donations** | Blender Foundation model — grants, sponsors, donations. | Community trust, mission-aligned, funds stewardship. | Hard to fund a fast team; not a growth engine. | Good **stewardship shell**, not the whole model. |
| **D. Crypto-native protocol** | Zone-C economics: compute take-rate, mint/marketplace/licensing/royalty fees. | Uniquely yours; scales with usage; aligns creators. | Regulatory ⚖️; needs the chain + liquidity + audience first. | **Differentiator**, phase-in. |

These are **not exclusive.** The right answer is a hybrid: **A + D, wrapped in a C-style stewardship shell,
with B as low-effort convenience revenue.**

---

## 5. Recommended model
**"Open core-app, proprietary network + protocol services, foundation-stewarded."**

1. **Zone A (app): free, GPL, best-in-class.** Adoption + brand + community are the asset. Don't try to
   monetize the binary beyond convenience (stream #13/14).
2. **Zone B (services): the recurring-revenue engine.** Lead with the three highest-moat services:
   **Eval-as-a-Service (#3), managed training (#2), hosted gallery (#4)** — each maps directly to a pillar,
   so building the app builds the service. Add inference/render/teams as the audience grows.
3. **Zone C (protocol): the differentiator that compounds.** **DePIN compute take-rate (#8)** is the flagship
   — it turns "local-first, cloud-optional, DePIN-capable" [D-2.4/3.2] into usage-scaled revenue without
   seats. Layer mint/marketplace/licensing (#9–11) as the creator economy matures. Keep provenance (#12)
   free to drive adoption of the whole loop.
4. **Stewardship shell:** a lightweight foundation/entity owns the **trademark + official builds + domain**
   (the moat) and funds core-app stewardship from a slice of Zone-B/C revenue — preserving OSS trust when
   the repo opens at v1 [D-8.3].

**Why this and not paid-binary open-core:** GPL makes closed in-app features impossible, and paid binaries
leak. Services + protocol are where GPL *lets* you charge, and they happen to be exactly your differentiated
pillars (eval, training, DePIN, chain). The business model and the architecture are the same shape.

---

## 6. Phasing (maps to the OSS-at-v1 plan [D-8.3])
- **Phase 0 — pre-v1 (private, small team).** Repo stays private; build the app + the *seams* for Zones B/C
  (backend adapters, eval SDK boundary, chain/pinning/identity adapters). No monetization yet. Register the
  **"Splendor" trademark** and secure domains early. ⚖️ counsel engaged on token/custody/marketplace.
- **Phase 1 — v1 OSS launch.** Open the mirrored repo. Ship free app + **one paid service live** (recommend
  **hosted gallery**, lowest-effort/high-network-effect) + **free provenance/attestation** to seed the loop.
- **Phase 2 — services layer.** Add Eval-as-a-Service, managed training, inference. Introduce **DePIN
  compute take-rate** as usage grows.
- **Phase 3 — creator economy.** Marketplace, licensing/royalties, secondary markets. Evaluate token
  *only* with counsel and real utility demand.

---

## 7. Hard cautions & mitigations
### 7.1 Fork-of-your-fork
GPL lets anyone rebrand Splendor (minus your trademark) and ship it. **Mitigation:** trademark + official
builds + the hosted network + community are the moat, not the code. This is normal and survivable (it's
Blender's own reality). Don't fight it; out-execute on Zones B/C.

### 7.2 Competitors hosting your services
Because the app is open, a competitor could point it at *their* backend. **Mitigation:** the services are
closed (Zone B), account-gated, and network-effect-backed (gallery, leaderboard, DePIN liquidity). Bundle
identity [D-5.4] + provenance so the default path is your network.

### 7.3 Protect your *own* server code with AGPL
For server components **you author** (not derived from Blender) — e.g. the hosted eval/training/gallery
backends — consider **AGPLv3 or proprietary** licensing so a competitor can't run your service code without
either contributing back or paying. You may license your own independent code however you like; you may
**not** relicense inherited Blender code. Keep the boundary clean and documented. ⚖️

### 7.4 Custody & account-abstraction [D-5.4]
If Splendor manages smart accounts / gas / keys for users, you may trip **money-transmission / custody**
rules depending on jurisdiction and design. Prefer non-custodial AA (user holds keys; you sponsor gas) and
get counsel before any custodial flow. ⚖️

### 7.5 Mint / marketplace / royalties
Primary sales, marketplace fees, and especially **any token** raise **securities, AML/KYC, and consumer-
protection** questions. Design fees as consumptive/utility, keep provenance free, and **do not ship a token
without securities counsel and a genuine non-investment utility.** ⚖️⚖️

### 7.6 GPL compliance hygiene
Publish complete corresponding source for every distributed build; keep third-party license notices
(Blender vendors many deps); document the app/service boundary so the "arm's-length service" argument holds.

---

## 8. Trademark & brand strategy (the actual moat)
- Register **"Splendor"** word mark + logo in relevant classes (software; online services). Secure
  `splendor.*` domains and social handles now (Phase 0).
- Reserve **"official build"** status: community can fork the code, but only your builds carry the mark —
  exactly how Blender/Firefox/Red Hat retain a canonical center.
- A trademark-usage policy at v1 OSS launch (what community forks may/may not call themselves).

---

## 9. Open legal questions for counsel (⚖️)
1. Confirm the arm's-length boundary for any non-GPL service code Splendor calls (§1.2, §7.3).
2. AGPL-vs-proprietary choice for your own server components (§7.3).
3. Custody/money-transmission analysis for AA/gas sponsorship (§7.4).
4. Securities/AML posture for mint, marketplace, royalties, and any token (§7.5, §7).
5. Trademark filing strategy + classes (§8).

---

## 10. Decisions this asks of you
- [ ] **Adopt the recommended hybrid** (open app + Zone-B services + Zone-C protocol + stewardship shell)? Or
      steer toward a different archetype from §4?
- [ ] **First paid service at v1** — confirm **hosted gallery** (my rec) vs. eval-service vs. training.
- [ ] **DePIN take-rate as flagship Zone-C revenue** — in for the model, phased post-v1?
- [ ] **Trademark + domains in Phase 0** — greenlight to treat as an early action item?
- [ ] **Token: off the table for now** (utility-only, counsel-gated later) — agree?
- [ ] **Engage IP + securities counsel** before Phase 1 — agree this is a hard gate?

Once you answer these, I'll fold the resolution back into `DECISIONS.md` [D-1.4] and let it constrain the
P7 (Deploy/Chain) spec + the agentile scaffold's business/compliance epics.
```
