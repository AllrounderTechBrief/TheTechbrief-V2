# Hanuman Chalisa — Production Blueprint
Journey: **SHANTI → BHAKTI → SHAKTI → VEER RAS → DIVINE PROTECTION → SHANTI**

## 0. What the analysis found (measured, not guessed)

| File | What it is | Measured |
|---|---|---|
| `Hanuman_Chalisa_starting.wav` | Suno backing, 2:39, stereo | Rock-steady grid: strongest pulse **0.424 s = 141.5 BPM**, second peak 0.856 s = **70.1 BPM** (half-time). 39 % of energy below 150 Hz (bass-heavy), almost nothing above 4 kHz (dull), harmonic drone + constant clicks. Median pitch ≈ 138.5 Hz ≈ **C♯3**. |
| `Starting.m4a` | Your slow opening vocal, 0:54, mono 68 kbps (phone/AAC) | No metronomic grid (free-time). Phrases about 5–6 s. Median pitch ≈ 170 Hz (**≈F3**). |
| `Hanuman_chalisa_full_.m4a` | Your full vocal, 4:09, mono 68 kbps | No metronomic grid (free-time, rubato). About 6 syllable-onsets per second. Median pitch ≈ 204 Hz (**≈G♯3**). Level steady (−21 dB RMS across the whole take, no dynamic arc). |

Pitch figures are medians of voiced frames over the first 60 s; confirm with a tuner.

**Four problems to fix**
1. **Tempo mismatch.** The backing is a rigid 141.5 BPM loop but your voice breathes freely. A fixed loop will drift against the vocal. Fix: build the percussion from a *tempo map of your vocal* (§3), or use a tool that generates around the vocal.
2. **Pitch mismatch.** The opening vocal sits about 4 semitones below the main vocal, and the backing's centre is C♯. A single drone cannot suit both. Fix: pick one Sa (§2).
3. **No energy arc.** The backing and vocal are flat for 4 minutes. This is a fatigue point.
4. **Low-quality source.** Both vocals are mono 68 kbps AAC. Re-export or re-record as WAV 48 kHz 24-bit (dry, no effects). Compression artefacts will show on a premium master.

## 1. Tempo and rhythmic feel
- **Master grid: 141 BPM.** It matches your 140–141 feel and the backing's 141.5.
- **Opening (Doha / intro): half-time, 70.5 BPM.** Same grid, tabla plays every second beat, so there is no tempo jump. At the first chaupai the feel **doubles** to 141. This gives "Shanti then Bhakti" without sleepiness.
- **Groove:** 8-beat Keherwa/Dadra family in a devotional bhajan style (not a dance beat). Tabla ge-na-ti-na with dholak bass. Accent the "1" with a soft dha. Add light syncopated *tihai*-style fills only at line endings.
- **Rubato rule:** your voice sets the tempo. Place the first beat of each line on the first syllable you actually sing (§3).

## 2. Key and drone
- Choose **Sa = C♯ (138.6 Hz)**. The backing already sits there and your main vocal's centre (G♯, the Pa) fits cleanly.
- **Opening vocal:** re-record it once at the main pitch, or transpose by about +4 semitones with formant-preserving shift (small shifts keep identity). Do not leave two tonics in one track.
- Tanpura: Pa–Sa–Sa–Sa (low Sa). Keep it continuous under the whole track. This makes the loop/ending smooth.

## 3. How to build it around your voice
1. Export your vocal as dry WAV.
2. Make a **marker track**: drop a marker on the first syllable of each of the 86 lines (Doha 2 + Chaupai 80 + closing Doha 2 + any repeats). A DAW's strip-silence or transient markers will place most of them; correct by ear.
3. Convert markers to a tempo map (each line ≈ 8 beats). Draw the tabla and dholak to that map, so the groove stretches and compresses with you.
4. Generate or play instruments in sections (below), not as one loop.
5. If using Suno: use *Add Instrumental* / Studio on your uploaded vocal (if your plan offers it), ask for **instrumental only, 141 BPM, key C♯**, and never "cover" or "persona" (that replaces your voice). Generate per section and pick the best take for each. A full-song single generation will not follow rubato.

## 4. Section-by-section energy plan (approximate times in the 4:09 take; verify with your markers)

Estimate: opening Doha 0:00–0:14, then about 5.6 s per chaupai, closing Doha 3:59–4:09.

| Time | Verses | Phase | Music |
|---|---|---|---|
| 0:00–0:14 (and intro) | Doha 1–2 | **SHANTI** | Tanpura, one bell, bansuri phrase (6–10 s intro as you asked). Half-time tabla enters softly at the end of the intro. Vocal in by about 0:08. |
| 0:14–0:59 | Ch. 1–8 | **BHAKTI** | Doubling to 141. Harmonium pad, light tabla, soft dholak, bell on line starts. Veena answers on each line end. |
| 0:25–0:31 | Ch. 3 "Mahabir bikram bajrangi" | accent | First *shakti* hint: add pakhawaj low hit and dholak bass for 2 lines, then pull back. |
| 0:59–1:21 | Ch. 9–12 (Sukshma roop, Bhim roop, Sanjivan) | **SHAKTI** (narrative) | More movement: dholak fills, bansuri running responses, santoor shimmer. Stronger low tabla. |
| 1:21–1:50 | Ch. 13–17 (Sahas badan, Sankadik, Yam Kuber, Sugriv, Vibhishan) | cooling / majesty | Drop percussion density 30 %, add harmonium chords and conch ambience. Contrast keeps listeners engaged. |
| 1:50–2:06 | Ch. 18–20 (Yug sahastra, Prabhu mudrika, Durgam kaj) | **VEER RAS 1** | Pakhawaj returns, dholak driving, low ceremonial drum on beat 1 of each line. |
| 2:06–2:35 | Ch. 21–25 (Ram duware, Aapan tej, Bhoot pisaach…) | **VEER RAS 2 peak** | Strongest groove so far. Tabla tihai at line ends. Keep the vocal 3 dB above the music. |
| 2:35–3:03 | Ch. 26–30 (Sankat te Hanuman chhudavai…) | **DIVINE PROTECTION** | Deep, steady: pakhawaj + dholak, warmer low end, sustained harmonium. Power by weight, not volume. |
| 3:03–3:36 | Ch. 31–36 (Ashta siddhi, Ram rasayan, Anta kaal…) | back to Bhakti | Percussion thins, bansuri and veena lead responses. Emotional release. |
| 3:36–3:42 | Ch. 37 "Jai Jai Jai Hanuman Gosain" | **strongest lift** | All instruments in, conch hit, bell flourish, tabla tihai into the line. |
| 3:42–3:59 | Ch. 38–40 | descent | Remove dholak, then pakhawaj, then tabla. Harmonium holds. |
| 3:59–4:09 | Closing Doha | **SHANTI** | Tanpura, one bell, bansuri; same sound as the intro. |

Rules: every transition has a 1-bar build (e.g. dholak roll or bell) and lands on the first syllable of a line. No section change mid-word.

## 5. Instrumentation and panning

| Instrument | Role | Pan | Notes |
|---|---|---|---|
| Tanpura | Continuous bed | wide L/R | Low in mix (−24 dB below vocal), never stops |
| Harmonium | Warm chords | L 25 % | Cut 250 Hz mud, keep 400–900 Hz open |
| Bansuri | Responses between lines | R 40 % | Short phrases only, mostly on line gaps |
| Veena or santoor | Answers, shimmer | L 40 % | One or the other per section, not both |
| Tabla | Main pulse | centre-left | Lower the treble clicks vs. current backing |
| Dholak | Bass body | centre | Raise only in Shakti and Veer sections |
| Pakhawaj | Weight | centre | Sparse, line-start hits |
| Bells | Phrase markers | R, wide | At section starts only |
| Conch | Ceremonial | centre, distant | 2–3 times total |

## 6. Vocal mixing approach
Vocal is the loudest element throughout. Chain (also in `vocal_prep.sh`):
1. High-pass 75 Hz, light denoise (nr 8 dB).
2. EQ: −2.5 dB at 220 Hz (boxiness), +2 dB at 3.2 kHz (consonant clarity), −3 dB shelf at 7.5 kHz (harshness).
3. Compressor about 2.4:1, 12 ms attack, 180 ms release, 2–3 dB gain reduction. Keep breaths.
4. Short temple-room reverb: 40–110 ms early reflections, plate 1.4 s decay, 12–15 % wet, high-cut at 5 kHz, pre-delay 30 ms. Duck the reverb 3 dB under words.
5. No autotune, no doubling, no stereo widening on the voice. A mono-centre vocal with the instrument bed wide is the premium sound.
6. Automate the vocal up 1–1.5 dB in Veer sections and down 1 dB in Shanti sections for natural dynamics.

A preview of this chain on your full vocal (`vocal_prep_preview.m4a`) was rendered with no change to pitch or timing.

## 7. Mix and low end
- Clean low end: high-pass everything except dholak/pakhawaj/tanpura at 60–80 Hz. Tabla high-pass 100 Hz.
- The current Suno backing has 39 % of its energy below 150 Hz. Cut that to about 22 % (shelf −4 dB under 120 Hz, notch the 70–90 Hz buildup) and add 2 dB of air above 8 kHz so it stops sounding dull.
- Side-chain: duck music 2–3 dB on vocal phrases (fast attack, 150 ms release).
- Mid cut at 1–3 kHz on the instruments (−2 dB) so every syllable stays intelligible.

## 8. Ending and loop design
- Closing Doha resolves to Sa on the tanpura. Let the tanpura + one bell ring out for 8–10 s with a natural decay (no fade-out gate).
- The first 3 s of the intro is the same tanpura, so the end crossfades into the start (1 s overlap, equal-power). Looping is seamless.
- For YouTube: 3 loops back to back works for a 12 min meditation version.

## 9. Mastering / delivery
- Master: stereo, **−14 LUFS integrated, true peak ≤ −1.0 dBTP**, LRA 6–9 LU. Gentle bus compression (1.5:1), no heavy limiting.
- Check on phone speaker, earbuds and laptop. Words must stay intelligible on the phone speaker.
- Deliverables: WAV 48 kHz 24-bit master, AAC for video, and a stem pack (vocal, tanpura bed, percussion, melody).

## 10. Specific fixes to the current Suno backing
- Remove the always-on click texture (it makes the track mechanical).
- Rebuild percussion section by section (§4) instead of one pattern.
- Raise tanpura, lower bass.
- Do not use its 141.5 BPM loop under the vocal as it is. Re-time to the vocal (§3).

## 11. Video plan (to follow once the final mix exists)
- 1080p YouTube cinematic: the Ram parivar images for Bhakti and Protection sections, the new Hanuman images (meditating Hanuman at sunrise, temple Hanuman with gada) for Shanti, Shakti and Veer sections.
- Visual arc mirrors the audio: soft golden dawn (Shanti) → warm temple (Bhakti) → stronger zooms and light rays (Shakti) → high-contrast fire-gold glow (Veer) → soft blessing glow (Protection) → dawn again (Shanti).
- Lyrics: Devanagari + Roman per line, timed from the marker track.
