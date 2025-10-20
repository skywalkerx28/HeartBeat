# Heartbeat **Clip Retriever** Design & Implementation Plan

> **Goal:** Enable the LLM to answer hockey questions like
> “Show me my shifts from the last five games,”
> “Show me all ozone clips from the last five games,” and
> “Show me all of my d‑zone exits clips from the last game,”
> by **retrieving + cutting** the right segments from our period-filtered MP4s using **play‑by‑play (PBP)** timestamps, then returning structured clips and metadata for the orchestrator to synthesize and present.

---

## Table of Contents

1. [Objectives & Non‑Goals](#objectives--non-goals)
2. [Assumptions](#assumptions)
3. [High‑Level Architecture](#high-level-architecture)
4. [Data Contracts & Schemas](#data-contracts--schemas)
5. [NL Query → Structured Params](#nl-query--structured-params)
6. [Event Retrieval From PBP](#event-retrieval-from-pbp)
7. [Video Cutting Pipeline](#video-cutting-pipeline)
8. [Orchestrator Integration](#orchestrator-integration)
9. [API/SDK Contracts](#apisdk-contracts)
10. [Role‑Based Access Control (RBAC)](#role-based-access-control-rbac)
11. [Performance, Caching, & Scaling](#performance-caching--scaling)
12. [Observability & Quality](#observability--quality)
13. [Edge Cases & Fallbacks](#edge-cases--fallbacks)
14. [Testing Strategy](#testing-strategy)
15. [Rollout Plan](#rollout-plan)
16. [Future Enhancements](#future-enhancements)
17. [Appendix A — Event Taxonomy](#appendix-a--event-taxonomy)
18. [Appendix B — FFmpeg Command Cheatsheet](#appendix-b--ffmpeg-command-cheatsheet)

---

## Objectives & Non‑Goals

### Objectives

* Parse chat queries into **structured clip search parameters** (players, event types, timeframe, opponent).
* Use **PBP events** (period, periodTime, gameTime, *timecode*) to map to **period MP4** offsets.
* **Cut** clips (pre/post context) fast & accurately; **thumbnail** generation.
* Return **structured `ClipResult[]`** + metadata so LLM can **summarize** and UI can **embed** playable clips.
* Follow **Perplexity‑style retrieval‑augmented synthesis** (transparent sources, concise summaries).

### Non‑Goals (for v1)

* No CV-based player tracking or optical identification (metadata‑driven only).
* No multi-camera stitching or broadcast ad-detection.
* No in‑clip overlays/graphics in v1 (optional later).

---

## Assumptions

* **Videos:** MP4s already **split per period** (e.g., `.../game_<id>_p1.mp4`, `p2.mp4`, `p3.mp4`, possibly OT).
* **PBP:** Available as **CSV/JSON** with fields including player(s), event type, period, periodTime, gameTime, **timecode** (real elapsed since period start), outcome, game id, opponent.
* **Orchestrator:** Existing LLM tool‑calling framework; we will add a **`retrieve_clips`** tool/node.
* **Queries:** Text chat.
* **Video Editing:** We will integrate **FFmpeg** (CPU; optional NVENC later).
* **RBAC:** Players see **their** clips; coaches/analysts broader access.

---

## High‑Level Architecture

```
[Chat UI]
   │
   ▼
[Orchestrator]
   ├─ Intent/Router → decides to call retrieve_clips
   │
   └─ Tool: ClipRetrieverNode
        │
        ├─ Query Parser (NL → ClipSearchParams)
        ├─ Event Store (PBP query)
        ├─ Source Video Resolver (game, period → file)
        ├─ Clip Generator (FFmpeg cut; thumbnails)
        ├─ Clip Index/Cache (persist + lookup)
        │
        └─ Output: ClipResult[] + provenance
   │
   ▼
[LLM Synthesizer]
   │  consumes ClipResult[] & analytics
   ▼
[Answer + Embedded Clips in UI]
```

**Design principle:** make retrieval **deterministic, explainable**, and **fast**. Treat clips as “documents” that the LLM cites and narrates (Perplexity‑inspired).

---

## Data Contracts & Schemas

### 1) `ClipSearchParams` (input to clip retriever)

```json
{
  "players": ["Nick Suzuki"],        // or inferred from user context if "my"/"me"
  "team": "MTL",                     // optional; inferred if needed
  "opponents": ["TOR"],              // optional
  "event_types": ["zone_exit"],      // see Appendix A
  "timeframe": "last_5_games",       // one of: last_game, last_3_games, last_5_games, this_season, date_range
  "date_range": {"from": "2024-10-01", "to": "2024-10-15"},
  "game_ids": [],                    // optional explicit list
  "limit": 10,                       // clip count cap
  "clip_window": {"pre_s": 3.0, "post_s": 5.0}, // for atomic events
  "mode": "event"                    // "event" | "shift"
}
```

### 2) PBP Event Record (CSV/JSON)

```json
{
  "game_id": "20241012-MTL-TOR",
  "game_date": "2024-10-12",
  "team": "MTL",
  "opponent": "TOR",
  "period": 2,
  "period_time": "12:34",       // mm:ss
  "game_time_s": 32*60+34,      // optional
  "timecode_s": 350.5,          // elapsed RL seconds since period start
  "players": ["Nick Suzuki"],
  "event_type": "zone_exit",    // normalized
  "outcome": "successful",      // optional
  "extra": {...}                // arbitrary fields (strength, zone, xG, etc.)
}
```

### 3) `ClipResult` (output)

```json
{
  "clip_id": "clip_20241012_MTL_TOR_p2_12m34s_suzuki_zoneexit",
  "title": "Nick Suzuki — D‑zone Exit vs TOR (P2 12:34)",
  "description": "Controlled exit along right boards (successful).",
  "player": "Nick Suzuki",
  "team": "MTL",
  "opponent": "TOR",
  "game_id": "20241012-MTL-TOR",
  "game_date": "2024-10-12",
  "period": 2,
  "period_time": "12:34",
  "start_timecode_s": 345.5,
  "end_timecode_s": 355.5,
  "duration_s": 10.0,
  "event_type": "zone_exit",
  "outcome": "successful",
  "file_path": "/clips/generated/20241012/MTL-TOR/p2/suzuki_zoneexit_12m34s.mp4",
  "file_url": "/api/v1/clips/clip_20241012_MTL_TOR_p2_12m34s_suzuki_zoneexit/video",
  "thumbnail_url": "/api/v1/clips/clip_20241012_MTL_TOR_p2_12m34s_suzuki_zoneexit/thumb.jpg",
  "provenance": {
    "source_video": "/video/20241012/MTL-TOR_p2.mp4",
    "pbp_event_id": "evt_f1c2..."
  }
}
```

---

## NL Query → Structured Params

**Parser responsibilities**

* **Players**: map names/aliases; resolve **“my/me”** using `user_context.player_id`.
* **Event types**: map hockey terms to taxonomy (Appendix A).

  * “ozone/oz” → offensive zone context → primarily `zone_entry`, optionally `oz_possession/shot/chance` if present.
  * “dzone exits/clears/breakouts” → `zone_exit` (+ outcome filters).
  * “shifts” → `mode = "shift"` (use shift intervals instead of atomic events).
* **Timeframe**: detect “last game”, “last N games”, “this season”, or date range.
* **Opponents**: detect “vs TOR”, “against Boston”, etc.
* **Defaults**: `limit=10`, `clip_window=(pre=3, post=5)`; `mode="event"`.

**Pseudocode**

```python
def parse_query(q: str, user_ctx) -> ClipSearchParams:
    players = extract_players(q) or ([user_ctx.player_name] if mentions_me(q) else [])
    event_types, mode = map_terms_to_events(q)  # e.g., "d-zone exits" → ["zone_exit"], mode="event"
    timeframe = detect_timeframe(q)             # e.g., "last five games"
    opponents = extract_opponents(q)
    return ClipSearchParams(
        players=players, event_types=event_types, opponents=opponents,
        timeframe=timeframe, limit=detect_limit(q) or 10,
        clip_window=detect_window(q) or {"pre_s":3,"post_s":5},
        mode=mode
    )
```

---

## Event Retrieval From PBP

**Steps**

1. **Resolve timeframe → game set**

   * `last_game`: last game for (player’s team) or last game where player dressed (if available).
   * `last_N_games`: previous N games (by date) for team/player.
   * `this_season`: all current season games (gate with `limit`).
   * Optional explicit `game_ids`.

2. **Filter PBP events**

   * Match `player in players` (or team if team‑level query).
   * Match `event_type in event_types` (taxonomy).
   * Match `opponent in opponents` (if provided).
   * Sort by game_date, then period, then timecode.

3. **Shift mode**

   * If `mode="shift"`, fetch **shift intervals** (start_timecode_s, end_timecode_s) for that player across target games.
   * Treat each shift as a clip (no pre/post).

**Implementation note**

* Prefer vectorized queries over CSV/Parquet (DuckDB/Polars/Pandas).
* Maintain a **game manifest** (game_id → date, opponent, available periods, video paths).

---

## Video Cutting Pipeline

**Mapping rule:** *timecode_s* is **seconds since period start**. If period MP4s start at the **exact period start**, then `offset_in_file = timecode_s`.
If not exact, maintain a **period manifest**:

```json
{
  "game_id": "20241012-MTL-TOR",
  "periods": {
    "1": {"video": ".../p1.mp4", "offset_s": 0.00},
    "2": {"video": ".../p2.mp4", "offset_s": 0.00},
    "3": {"video": ".../p3.mp4", "offset_s": 0.00},
    "OT": {"video": ".../ot.mp4", "offset_s": 0.00}
  }
}
```

**Cut strategy**

* For atomic events:
  `start = max(0, timecode_s - pre_s)`
  `end   = min(period_duration_s, timecode_s + post_s)`
* For shifts:
  `start = shift.start_timecode_s`, `end = shift.end_timecode_s`.

**FFmpeg options (v1 default: re-encode small segment)**

* Accurate, robust: `-ss <start> -to <end> -c:v libx264 -preset ultrafast -crf 20 -c:a aac -b:a 128k -movflags +faststart -pix_fmt yuv420p`
* Thumbnail: `-ss <start+1..5> -frames:v 1`

**Parallelism**

* Use a bounded **process pool** (e.g., max 4 concurrent cuts) to avoid CPU saturation.

**File layout**

```
/clips/generated/<season>/<game_id>/<period>/
  <slug>_<mmss>_<event>.mp4
  <same>.jpg  (thumbnail)
```

**Clip metadata**

* Write a small **sidecar JSON** per clip or append to an **index DB** (SQLite/DuckDB) for fast lookups.

---

## Orchestrator Integration

### New Tool: `retrieve_clips`

**Tool schema (JSON schema snippet)**

```json
{
  "type": "object",
  "properties": {
    "players": {"type": "array", "items": {"type": "string"}},
    "opponents": {"type": "array", "items": {"type": "string"}},
    "event_types": {"type": "array", "items": {"type": "string"}},
    "timeframe": {"type": "string", "enum": ["last_game","last_3_games","last_5_games","this_season","date_range"]},
    "date_range": {"type": "object", "properties": {
      "from": {"type":"string","format":"date"}, "to":{"type":"string","format":"date"}
    }},
    "game_ids": {"type": "array", "items": {"type":"string"}},
    "limit": {"type":"integer","minimum":1,"maximum":100},
    "clip_window": {"type":"object","properties":{
      "pre_s":{"type":"number","minimum":0,"maximum":30},
      "post_s":{"type":"number","minimum":0,"maximum":30}
    }},
    "mode": {"type":"string","enum":["event","shift"]}
  },
  "required": ["event_types","timeframe"]
}
```

### Node contract

```python
async def clip_retriever_node(state) -> dict:
    params = parse_query(state["user_query"], state["user_context"])
    events_or_shifts = query_pbp(params)
    clips = await generate_and_index_clips(events_or_shifts, params)
    tool_result = {
      "tool": "retrieve_clips",
      "ok": True,
      "used_params": params,
      "clips": clips,
      "metrics": {"events": len(events_or_shifts), "clips": len(clips), "ms": ...}
    }
    # expose to downstream synthesizer
    state.setdefault("visual", {})["clips"] = clips
    state.setdefault("tool_results", []).append(tool_result)
    return state
```

### LLM synthesis

* Prompt includes: *“You have `visual.clips` (list of clips). Summarize concisely, enumerate with period:time, outcome. Keep text skimmable. Reference the clips by title.”*
* UI reads `clips[]` to render playable videos with thumbnails under the answer.

---

## API/SDK Contracts

### Clip playback (server)

* `GET /api/v1/clips/{clip_id}/video` → `video/mp4` (supports range requests).
* `GET /api/v1/clips/{clip_id}/thumbnail` → `image/jpeg`.
* (Optional) `GET /api/v1/clips/search?...` for dev/testing.

### Orchestrator response bundle

```json
{
  "answer": "Here are your d‑zone exits from Oct 12 vs TOR...",
  "clips": [ClipResult, ...],
  "citations": ["pbp:events=3", "video:20241012-MTL-TOR"]
}
```

---

## Role‑Based Access Control (RBAC)

* **PLAYER**: can request **own** clips only (enforce `(player_id == user_ctx.player_id)`); team‑level only if explicitly allowed.
* **COACH/ANALYST**: team‑wide; can filter by any player/opponent.
* **ADMIN**: all.
* Enforce **on PBP query** and **again** before serving files.
* Generate error message if filters violate access (e.g., “No permission to view other players’ clips”).

---

## Performance, Caching, & Scaling

* **Index DB** (SQLite/DuckDB) for:

  * Known pre‑cut clips (goals/saves/etc.).
  * Newly generated clips (append on write).
* **Caching:** memoize PBP queries by (player,event,timeframe,opponent).
* **Clip reuse:** if a requested segment already exists within ±0.5s bounds, **reuse** file.
* **FFmpeg tuning:** `-preset ultrafast`, `-movflags +faststart`, small GOP if re‑encoding; optional **NVENC** for GPU servers.
* **Concurrency:** bounded workers; back‑pressure if the queue grows.
* **SLA (targets):**

  * PBP query: < 150 ms
  * Cut 10 × 8‑sec clips (CPU): ~2–4 s total (parallel 3–4 procs)
  * First byte to UI: < 3 s for small requests

---

## Observability & Quality

* **Structured logs** per clip: game_id, period, event_type, t_start/t_end, duration, ffmpeg exit code, ms.
* **Metrics:** counters (clips_generated, cache_hits), histograms (cut_duration_ms).
* **Tracing:** Orchestrator span → ClipRetriever → PBP query → FFmpeg subprocess.
* **Validation:**

  * Verify `start < end`, duration clamp (e.g., ≤ 30 s default for events).
  * Ensure clip boundaries within video length.
  * Thumbnail existence.

---

## Edge Cases & Fallbacks

* **Ambiguous “my”** with unknown player → default to user’s team or prompt the LLM to ask follow‑up (only if our UX allows).
* **No events found** → friendly message + offer nearest alternatives (e.g., “No d‑zone exits; showing recoveries/clears”).
* **Overtime/SO** → include as extra period; ensure manifest has OT video.
* **Missing/shifted timecodes** → if period offset mismatch detected, apply `offset_s` from manifest or heuristic against nearby events.
* **Large result sets** (e.g., last 5 games zone entries) → cap by `limit`, or group by game and return top N per game.
* **File not found** → return 404 with remediation (re‑ingest game video or rebuild manifest).
* **Trades/jersey name variants** → maintain alias map (player_id‑centric).

---

## Testing Strategy

### Unit

* Parser → params (players, events, timeframe, opponents).
* Taxonomy mapping (ozone/dzone synonyms).
* Timecode → segment math (pre/post, clamping).

### Integration

* PBP query → events → cut → serve → UI playback.
* Shift mode across games.
* RBAC enforcement (player vs coach).

### E2E Scenarios

1. “Show me **my shifts** from the **last five games**.”
2. “Show me all **ozone** clips from the **last five games**.”
3. “Show me all of **my dzone exits** clips from the **last game**.”

Verify: correct games chosen, correct periods, clip durations, playable in UI, coherent LLM summary.

---

## Rollout Plan

1. **Phase 1 — Foundations (D1–D3)**

   * Define taxonomy, parser, and params.
   * Implement PBP query layer + game/period manifest.
   * Build FFmpeg wrapper + single‑clip cut.

2. **Phase 2 — Tool Integration (D4–D6)**

   * Implement `ClipRetrieverNode`.
   * Build clip index & caching.
   * Add API endpoints for clip/thumbnail.

3. **Phase 3 — UI & Synthesis (D7–D8)**

   * Wire `clips[]` into chat responses.
   * Prompt tuning for concise bullet summaries.

4. **Phase 4 — Hardening (D9–D10)**

   * RBAC, observability, rate limits.
   * E2E tests, perf tuning, pre‑cut hot events.

---

## Future Enhancements

* **GPU NVENC** acceleration.
* **Pre‑cut library** for common asks (goals, PP entries, PK clears).
* **Playlists** (coach collections), export/share.
* **Vision assist** (Q&A over frames, player confirmation).
* **Richer event chains** (entry → sustained OZ possession → chance).
* **Automatic best‑of selection** using metrics (e.g., only successful exits under pressure).

---

## Appendix A — Event Taxonomy

| User term(s)                                           | Normalized `event_type`          | Notes                                             |
| ------------------------------------------------------ | -------------------------------- | ------------------------------------------------- |
| goal, scored                                           | `goal`                           | pre‑existing pre‑cuts likely                      |
| assist, primary assist, secondary assist               | `assist`                         |                                                   |
| save, shot against                                     | `save`                           | goalie clips                                      |
| shot, chance, SOG, slot look                           | `shot`, `chance`                 |                                                   |
| power play, PP entry, PP setup                         | `zone_entry`, `pp_setup`         | optional                                          |
| penalty, draw penalty                                  | `penalty_drawn`, `penalty`       |                                                   |
| **ozone**, offensive zone, OZ entry, carry‑in, dump-in | `zone_entry` (+ `oz_possession`) | interpret “ozone clips” as OZ entries/possessions |
| **dzone exits**, breakout, clear, glass‑and‑out        | `zone_exit`                      | outcome success/fail if available                 |
| forecheck, retrieval                                   | `forecheck`, `puck_recovery`     | optional                                          |
| **shifts**                                             | `mode="shift"`                   | use shift intervals                               |

*(Extend as needed to your PBP schema.)*

---

## Appendix B — FFmpeg Command Cheatsheet

**Accurate re‑encode (recommended default)**

```bash
ffmpeg -hide_banner -loglevel error \
  -ss {START_S} -to {END_S} -i "{SRC_MP4}" \
  -c:v libx264 -preset ultrafast -crf 20 \
  -c:a aac -b:a 128k -movflags +faststart -pix_fmt yuv420p \
  -y "{OUT_MP4}"
```

**Faster seek + accurate refine (two‑ss technique)**

```bash
ffmpeg -hide_banner -loglevel error \
  -ss {START_S-1} -i "{SRC_MP4}" -ss 1 -to {DURATION_S} \
  -c:v libx264 -preset ultrafast -crf 20 \
  -c:a aac -b:a 128k -movflags +faststart -pix_fmt yuv420p \
  -y "{OUT_MP4}"
```

**Thumbnail @ 5s into clip**

```bash
ffmpeg -hide_banner -loglevel error \
  -ss 5 -i "{OUT_MP4}" -frames:v 1 -qscale:v 2 -y "{OUT_JPG}"
```

---

### Example End‑to‑End (D‑zone exits, last game)

1. **Parse** →

```json
{
  "players":["Cole Caufield"],
  "event_types":["zone_exit"],
  "timeframe":"last_game",
  "clip_window":{"pre_s":3,"post_s":5},
  "mode":"event"
}
```

2. **Query PBP** → 3 matching events (P1 10:05, P2 07:20, P3 14:45).

3. **Resolve videos** → `/video/20241012/MTL-TOR_p1.mp4`, `_p2.mp4`, `_p3.mp4`.

4. **Generate clips** (3 files + thumbnails) and persist index.

5. **Orchestrator Response** → LLM enumerates clips with brief context; UI renders playable videos.

---

**This plan is ready to implement.** If you want, I can also produce skeleton code stubs (parser, FFmpeg wrapper, node integration) to drop into the repo.
