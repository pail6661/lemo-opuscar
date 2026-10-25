---
name: lemo-opuscar
description: 用 Lemo-Opuscar 风格库实际制作代码渲染的视频、动画、宣传片、科普片和纪实短片，或创建并复用个人风格。适用于选风格、分镜、配音配乐、渲染和交付完整工程；普通视频裁剪、转码不需要此技能。
---

# Lemo-Opuscar for Codex

Use the Lemo-Opuscar library to direct and **produce real local files**. This is a Codex entrypoint for the upstream library by **Lemomo / LemoLab**, not a video model or a browser chat rendering service. Keep its MIT notices and the separate licences of its sample films and third-party assets.

## Find the library and prepare it

Resolve `$LIB` in this order, validating that it contains `CODEX.md`, `core/render/video.mjs` and `styles/README.md`:

1. The user's current repository, searching the current directory and its parents.
2. The `LEMO_OPUSCAR_HOME` environment variable.
3. The path in `library-path.txt` beside this installed `SKILL.md`, when the local installer supplied that file. This is a machine-local pointer, not a path to publish with the skill.

If a candidate is missing, continue to the next one. If none resolves, locate the user's existing checkout or ask only for its location; do not pretend the skill includes the whole library. Do not reset or auto-update a user's checkout. The full checkout includes demo source; a missing demo or asset is not proof of a successful download.

Read `$LIB/CODEX.md`, then `$LIB/AGENTS.md`. Use their directing and style workflow, with the Codex adaptations here and in `CODEX.md` taking precedence over Claude-specific commands. The model is the one the user selected in their current Codex session: no Claude login, Claude executable, fixed model name or extra API key is required for the core workflow. Model quality still needs to be checked on the actual output.

On Windows, prefer the native PowerShell tools; WSL is not required for this fork's shared pipeline:

```powershell
# Check the local environment without installing.
& "$LIB/tools/setup-codex.ps1" -Diagnose
# Install the core tier when the current task authorizes local setup.
& "$LIB/tools/setup-codex.ps1" -Tier core
```

Add `-Tier voice` only for narration and `-Tier music` when plucked-string modelling needs it; each includes core. Fetch only required assets with `setup-codex.ps1 -Assets`, for example `voice` or `hdri`. Check errors and actual readiness; an installed skill or downloaded model is not a rendered film. The setup and tool launcher manage their configured caches and the library virtual environment. Do not install packages globally or overwrite unrelated environments.

## Choose the entrypoint

Use the user's language and skip questions already answered. Check the user's saved style index at `~/lemo-my-styles/README.md` first (or their chosen personal-style location). Offer these four paths when they have not chosen:

1. Make a film in a library style.
2. Change a library style and save a personal version.
3. Create a personal style from a blank page.
4. Make a film in a saved personal style, when one exists.

For the library list, read `styles/README.md` or `styleboard/catalog.json`; do not invent styles or count `styles/_template` as a finished style. There are currently 59 library styles in 11 categories. The OPUSCAR98 page has 98 additional reusable style prompts, a separate collection rather than 98 complete library entries. When the user asks for all styles or has not chosen one, show the complete list as the upstream `AGENTS.md` requires, with two or three relevant recommendations and [the gallery](https://lemomo-ai.github.io/lemo-opuscar/).

## Make a film

Read `DIRECTOR.md`, `TECHNIQUE.md`, `core/README.md`, and the selected `styles/<slug>/STYLE.md` in full. The style defines materials, colour, type, motion, camera and sound; the user's topic determines the story. Treat upstream model references as the provenance of its examples, not a requirement to switch away from Codex.

- Establish only missing facts, required products/characters/branding, owned material, language, length, frame size and whether a storyboard review is wanted. Bundle necessary questions once; proceed on clear defaults. Narration text sent to an online TTS provider needs the user's authorization for that service; local Kokoro is available. No paid API use is implied by choosing this skill.
- Work in `films/<name>/` for a repository workflow, or `<name>/` in the user's chosen output folder. Do not modify `styles/`, `core/` or the library guides to produce a user's film. Keep original assets intact.
- Write an original `TREATMENT.md` before reading the demo's `DEMO.md` or drawing code. For Edit & Documentary, first gather and log source material, and use only its named material-acquisition tools before the treatment. For personal-style creation, follow the separate order in `MY-STYLES.md`.
- Prove the look using the real drawing code, then review a storyboard only if requested. Honor an explicit review checkpoint; otherwise continue through production.
- Produce and verify voice, score, animation, sound, subtitles and the final mix. Build a deterministic `window.render(t)` page with `window.READY`, `window.DUR`, and event/text hooks when needed. Use absolute browser URLs such as `/core/lib.js`; use filesystem paths for scripts. Lay out for the requested size; changing only render dimensions does not make a good vertical composition.

The PowerShell launcher is the native shared-tool interface. `-Arguments` is an array, so paths with spaces stay intact:

```powershell
$LEMO = Join-Path $LIB 'tools/lemo.ps1'
& $LEMO -Tool still -Arguments @($PROJECT, '1.5', '--size', '1920x1080')
& $LEMO -Tool render -Arguments @($PROJECT, '--fps', '24', '--out', "$PROJECT/out/video.mp4")
& $LEMO -Tool mux -Arguments @("$PROJECT/out/video.mp4", "$PROJECT/out/mix.wav", "$PROJECT/film.mp4", '24', '0')
```

Available tool names: `still`, `render`, `events`, `readcheck`, `mux`, `tts`, `tts-zh`, `asr`, `srt`, `sheet`, `fetch`. Read `CODEX.md` and the tool's `--help`/source for its arguments rather than inventing flags. `mux` calls `core/render/mux.py`, replacing the upstream shell-only mux command. When calling Python directly, use `$LIB/.venv/Scripts/python.exe` on Windows and `$LIB/.venv/bin/python` on POSIX. Style-specific dependencies belong in that film's private environment. Some demo `build.sh` files and acquisition tools still need POSIX utilities or adaptation; translate the needed operations into a project-local PowerShell/Python build instead of claiming every old demo is Windows-native.

## Create or keep a personal style

Read and follow `MY-STYLES.md`: choose one technique base, clarify the intended changes, explain which alter its character, render a real style frame (side-by-side with the base when modifying one), then a 15–30 second demo. Keep the full `STYLE.md`, `CHANGES.md`, metadata, approved frame, demo and source together. Do not replace the style's essence silently, overwrite an existing name, or make someone else's demo story the user's film. Use the user's existing approvals; otherwise show the concrete result and get confirmation before adding it to their permanent style index. Save outside the library so updates preserve it.

## Verify and deliver

Follow `DIRECTOR.md` §11 and `TECHNIQUE.md` §8: review contact sheets, key-action frame strips and the actual final file with sound; check page failures, missing media, subtitle/readability timing, ASR when there is speech, loudness and blank frames. Fix findings and recheck. Do not call tool availability, a still frame or successful mux proof of full viewing. If a check cannot be performed in the current environment, name that specific gap.

Deliver the MP4, `poster.jpg`, SRT when appropriate, `TREATMENT.md`, `CREDITS`, and full source with a one-command **`build.ps1` on Windows** (or `build.sh` for POSIX). Factual films also keep `FACTS.md` and source evidence. Retain upstream MIT notices in copied source and list asset licences in `CREDITS`; user films have no added LemoLab watermark or sign-off. Link the actual local outputs and separate prepared, rendered and reviewed states.

Codex App/CLI with local tools can execute this pipeline. A plain ChatGPT browser conversation can help plan or review supplied material but cannot access this installation or render locally without an execution connection. Never report a film as created when only its plan or prompt exists. Do not publish, upload or send the user's material without the corresponding request.
