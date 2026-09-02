# Next Phase Request: Fish Shell Automation + TTS Voice Enhancement

**Current Date**: 2026-09-02  
**Status**: Primary video pipeline work COMPLETE ✅

---

## What Was Just Completed

1. **Enhanced nightly_runner.py** with fault tolerance, retry logic, and QA gates ✅
2. **Created linting system** (.pylintrc, .flake8, .pre-commit-config.yaml) ✅
3. **Created SOP framework** (SOP_TEMPLATE.md for all domains, SOP_VIDEO_PIPELINE.md for video) ✅
4. **Generated deployment email** with clear next steps ✅

All work pushed to branch: `claude/file-org-harness-optimize-bpvx0i`

---

## New Request for Clarification

**User Message**: "review fish auto for our stack and see if we can enhance our tts, I would like move voice options"

### What We Need to Understand

1. **Fish Shell Automation ("fish auto")**
   - Is there an existing Fish shell script in the repo? (None found yet)
   - What should Fish automation do in your stack?
   - Is this for:
     - Orchestrating the video pipeline?
     - Scheduling renders?
     - Managing TTS input generation?
     - Something else?

2. **TTS Enhancement ("enhance our tts")**
   - What TTS system is currently in use?
     - HeyGen API (voice synthesis)?
     - Azure Cognitive Services?
     - Google Cloud TTS?
     - Custom TTS model?
   - What specific enhancement are you looking for?

3. **Voice Options ("I would like move voice options")**
   - What voices are you looking to enable?
     - Different languages? (Spanish, Mandarin, French, etc.)
     - Different accents? (British, Indian, Australian English)
     - Different genders? (male, female, neutral)
     - Different styles? (professional, casual, enthusiastic)
     - Different speakers/identities?
   
   - **Key question**: "Move voice options" — does this mean:
     - Move voice configuration from hardcoded to configurable?
     - Move voice generation to a different service?
     - Move voice options from one system to another?

---

## How to Clarify

Please provide:

```
1. Current TTS system: [HeyGen / Azure / Google Cloud / Custom / Other]
2. Current voice options available: [List what's currently supported]
3. New voice options needed: [List specific languages, accents, genders, etc.]
4. Integration point: [Where should Fish auto handle this?]
5. Example use case: [How would a video operator use this?]
```

**Example Response**:
```
1. Current TTS: HeyGen API (currently English only)
2. Current voices: 1 speaker (male English)
3. New voices needed: Spanish (México), French (France), British English
4. Integration: Fish script should let operators choose voice when submitting render jobs
5. Example: `render-video --input hero.json --voice spanish-mexico`
```

---

## Proposed Next Steps (Once Clarified)

### Option A: Configure Voice Selection in Job Queue
```bash
# jobs/queue.json enhancement
{
  "jobs": [
    {
      "name": "hero_video",
      "tts_voice": "spanish-mexico",  ← NEW
      "cmd": [...],
      ...
    }
  ]
}
```

### Option B: Create Fish Shell Helper Script
```bash
# ai-projects/render.fish — wrapper for nightly_runner.py
function render-video
  set -l voice $argv[1]  # "spanish-mexico", "british-english", etc.
  set -l input $argv[2]  # job config file
  python nightly_runner.py --queue $input --tts-voice $voice
end
```

### Option C: Enhance TTS Service Selection
```python
# In nightly_runner.py or new tts_manager.py
VOICE_OPTIONS = {
    "english-us": {"service": "heygen", "voice_id": "english_us_male"},
    "english-uk": {"service": "azure", "voice_id": "en-GB-RyanNeural"},
    "spanish-mx": {"service": "google", "voice_id": "es-MX-Neural2-C"},
}
```

---

## Questions for You

1. **Is "fish auto" an existing system, or new?**
   - If existing, where is the code?
   - If new, what problem should it solve?

2. **Do operators need to choose voice per job, or globally?**
   - Per-job (video A uses Spanish, video B uses English)?
   - Global (all renders use the same voice)?

3. **Should voice configuration be:**
   - In `jobs/queue.json`?
   - Command-line argument (`--tts-voice spanish-mexico`)?
   - Environment variable?
   - Web UI selector?

4. **How many voice options do you need to support?**
   - 5-10 languages?
   - 50+ language+accent combinations?

5. **Budget for TTS service cost?**
   - Should we optimize for cheapest TTS provider?
   - Is cost not a concern?

---

## Waiting For

Please clarify the questions above, and I'll:
- ✅ Design the Fish shell automation
- ✅ Integrate voice options into nightly_runner.py
- ✅ Create SOP for voice selection workflow
- ✅ Update job queue format (if needed)
- ✅ Test end-to-end with different voices

---

**Timeline**: Once clarified, implementation is 2-4 hours.

