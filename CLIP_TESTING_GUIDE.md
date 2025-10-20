# Clip Retrieval Testing Guide

**Status:** Function Registered - Ready to Test  
**Date:** October 14, 2025

---

## Quick Start

### 1. Restart Backend (IMPORTANT!)
```bash
# Stop current backend (Ctrl+C)
cd /Users/xavier.bouchard/Desktop/HeartBeat/backend
python main.py
```

The backend needs to be restarted to load the new `retrieve_video_clips` function.

### 2. Test Queries (Exact phrases to use)

#### SHIFT MODE QUERIES (Best to start with)

```
"Show me Beauvillier shifts from the game vs NYR in the first period"
```

**Expected:**
- Model calls `search_player_info` to find Beauvillier (player_id: 8478463)
- Model calls `retrieve_video_clips` with:
  - mode: "shift"
  - player_ids: [8478463]
  - periods: [1]
  - team: "WSH"
- Returns 3 shift clips with red SHIFT badges
- Each playable with thumbnail

---

```
"Show me all shifts in period 2 for Beauvillier"
```

**Expected:**
- Returns 5 shift clips from period 2
- Shows duration (48s, 191s, 181s, etc.)
- Shows strength (5v5)

---

#### EVENT MODE QUERIES

```
"Show me zone exits by Beauvillier in period 1"
```

**Expected:**
- Model calls `retrieve_video_clips` with:
  - mode: "event"
  - event_types: ["zone_exit"]
  - player_ids: [8478463]
  - periods: [1]
- Returns ~3 event clips with cyan EVENT badges

---

```
"Show me all offensive zone entries in the first period"
```

**Expected:**
- Returns zone entry event clips
- Cyan badges
- Short clips (8-10s with context)

---

### 3. What to Look For

#### In Backend Logs:
```
INFO - Executing (parallel): retrieve_video_clips(...) [#X]
INFO - Clip query found 3 segments
INFO - Cache hit for shift_20038_p1_0s_8478463
INFO - All clips cut successfully
INFO - Retrieved 3 shift clips for 1 player(s)
```

#### In Frontend UI:
```
[Video Clips Panel appears with header]

SHIFTS - PERIOD 1 (3 FOUND)
━━━━━━━━━━━━━━━━━━━━━━━━━
3 clips • 3 shifts • 0 events

[ALL] [SHIFTS] [EVENTS]  [Grid] [List]

[Red SHIFT Badge] [42s] [5v5]
Anthony Beauvillier - 42s Shift
Period 1 at 0:00 • 5v5 • vs 10 opponents
WSH vs NYR • 2025-10-12
[Playable Video Player]

[... 2 more shift clips ...]
```

---

## Debugging If It Doesn't Work

### Issue: Model doesn't call retrieve_video_clips

**Check Backend Logs For:**
```
Qwen3 Best Practices Orchestrator initialized with 20 tools
```

If it says 19 tools, the function didn't register.

**Solution:**
- Restart backend completely
- Check for Python syntax errors in the file

---

### Issue: Model calls get_live_play_by_play instead

This means the model doesn't understand to use the video tool.

**Solution:** Be more explicit in the query:
```
"Get me VIDEO CLIPS of Beauvillier's shifts in period 1"
"I want to SEE Beauvillier's zone exits, show me video"
```

---

### Issue: Function called but no clips returned

**Check Backend Logs:**
```
INFO - Clip query found 0 segments
```

**Possible Causes:**
1. Player ID not found - check spelling
2. Game ID mismatch - verify game 20038 exists
3. Period has no video - only period 1 available
4. No events match query

**Debug Command:**
```bash
cd /Users/xavier.bouchard/Desktop/HeartBeat
python3 scripts/test_comprehensive_clip_retrieval.py
```

Should show 9 clips indexed.

---

### Issue: Videos don't play in UI

**Check Browser Console:**
- CORS errors → Check API_BASE_URL
- 404 errors → Clips not in database
- 403 errors → Authentication issue

**Verify Clips:**
```bash
ls -lh /Users/xavier.bouchard/Desktop/HeartBeat/data/clips/generated/20038/p1/
```

Should show MP4 and JPG files.

---

## Advanced Test Queries

Once basic queries work, try these:

### Multi-Player
```
"Show me shifts for Beauvillier and Wilson in period 1"
```

### Opponent Filtering
```
"Show me Beauvillier's shifts when Zibanejad was on ice"
```

### Multi-Period
```
"Show me all zone exits in periods 1 and 2"
```

### Timeframe
```
"Show me shifts from the last 3 games"
```
(Note: Only game 20038 has video currently)

---

## Expected Performance

```
Query → Response Time:
- Player search: ~2s
- Clip query: ~0.5s
- Clip cutting: 0.01s (cached), 1-2s (new)
- UI render: ~0.3s
Total: ~3-5 seconds to playable video
```

---

## Success Criteria

### ✓ Basic Functionality
- [ ] Model calls retrieve_video_clips function
- [ ] Clips appear in UI below Stanley's message
- [ ] Video players are visible
- [ ] Thumbnails load
- [ ] Videos play when clicked

### ✓ Shift Mode
- [ ] Red SHIFT badges appear
- [ ] Durations correct (42s, 82s, 189s)
- [ ] Strength indicators (5v5)
- [ ] Full shifts are playable

### ✓ Event Mode
- [ ] Cyan EVENT badges appear
- [ ] Event types correct (CONTROLLED EXIT FROM DZ)
- [ ] Shorter clips (8-10s)

### ✓ Filtering
- [ ] ALL filter shows everything
- [ ] SHIFTS filter shows only shifts
- [ ] EVENTS filter shows only events
- [ ] Grid/List toggle works

### ✓ UX
- [ ] Hover shows controls
- [ ] Click plays smoothly
- [ ] Progress bar updates
- [ ] Mute toggle works
- [ ] Animations are smooth
- [ ] Design matches app aesthetic

---

## RECOMMENDED FIRST TEST

**Start with this exact query:**

```
"Show me Beauvillier shifts from the game vs NYR in the first period"
```

**Why this query:**
1. Specific player (Beauvillier = 8478463)
2. Specific game (WSH vs NYR = 20038)
3. Specific period (1 = we have video)
4. Shift mode (easier to see than short events)
5. Known to work (tested in scripts)

**Expected Result:**
- 3 video clips
- Red SHIFT badges
- Durations: 42s, 82s, 189s
- All playable

---

## If Everything Works

**Next Steps:**
1. Test with different players
2. Test event mode queries
3. Test filtering UI
4. Test on mobile/tablet
5. Gather more game videos
6. Deploy to staging

---

## If Nothing Works

**Emergency Debug:**
```bash
# Check orchestrator registration
cd /Users/xavier.bouchard/Desktop/HeartBeat
python3 -c "
from orchestrator.agents.qwen3_best_practices_orchestrator import Qwen3BestPracticesOrchestrator
orch = Qwen3BestPracticesOrchestrator()
print('Tools:', len(orch.all_tools))
print('Has retrieve_video_clips:', 'retrieve_video_clips' in orch.all_tools)
" 2>&1 | tail -5

# Verify clips exist
ls data/clips/generated/20038/p1/*.mp4 | wc -l

# Check database
python3 -c "
from orchestrator.tools.clip_index_db import get_clip_index
index = get_clip_index()
print('Clips in DB:', index.get_stats()['total_clips'])
" 2>&1 | tail -2
```

Expected output:
```
Tools: 20
Has retrieve_video_clips: True
4    (MP4 count)
Clips in DB: 9
```

---

## Notes

- Only **game 20038 (WSH vs NYR)** has video currently
- Only **period 1** video is clean and complete
- Player **8478463 (Beauvillier)** has the most test data
- Shift clips are **longer** (30s-3min) than events (8-10s)
- Clips are **cached** - second request is instant

---

**STATUS: Ready to Test!**

Restart the backend and try the first query. The model should now call `retrieve_video_clips` and return playable video clips in the UI.

