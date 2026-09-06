# Decky Framegen Plugin

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/B0B71HZTAX)

A Steam Deck plugin that enables DLSS upscaling and Frame Generation on handhelds by utilizing the latest OptiScaler and supporting modification software. This plugin automatically installs and manages all necessary components for FSR-based frame generation in games that support DLSS, or OptiFG for adding FG to games that do not have any existing FG pathway (highly experimental)

## What This Plugin Does

This plugin uses OptiScaler to replace DLSS calls with FSR3/FSR3.1, giving you:

- **Frame Generation**: Smooth out your frame rate using AMD's FSR3 pathways
- **Upscaling**: Improves performance while maintaining visual quality using FSR and XESS using DLSS FSR or XESS inputs. Upgrade FSR 2 games to FSR 3.1.4 or XESS for better visual quality.
- **Easy Management**: One-click installation and game patching/unpatching through the Steam Deck interface. No going into desktop mode every time you want to add or remove OptiScaler from a game!

## Features

### Core Functionality
- **One-Click Setup**: Automatically downloads and installs OptiScaler into a "fgmod" directory
- **Smart Installation**: Handles all required dependencies and library files
- **Game Patching**: Easy copy-paste launch commands for enabling/disabling the mod per game
- **OptiScaler Wiki**: Direct access to OptiScaler documentation and settings via a webpage launch button right inside the plugin.

## How to Use

1. **Install the Plugin**: download `Decky-Framegen.zip` from the release on the Deck, then in Gaming Mode open Decky → gear icon → **Developer** (enable *Developer mode* under General first if the tab is missing) → **Install Plugin from ZIP File** → Browse → pick the zip.
   - Requires Decky Loader 3.0.0 or newer (the plugin uses the `decky` Python module and plugin API v1; tested against 3.2.8).
   - **An Internet connection is required during install.** Decky Loader re-downloads the OptiScaler/FSR binaries listed in `package.json` (~360 MB) even though they are inside the zip, so the progress bar can sit near the end for a few minutes. If it ends with *"Could not download remote binaries"*, the files are already extracted: restart Decky Loader (Settings → General → Restart) or reboot, and the plugin loads from the bundled files.
   - **Keep the file named exactly `Decky-Framegen.zip`.** Decky names a zip install after the file name and only replaces an existing plugin when the names match; a renamed download (`Decky-Framegen (1).zip`) would be extracted over the old install instead. Alternatively uninstall the previous version first (Decky → Settings → Plugins). Uninstalling the plugin never touches `~/fgmod`, patched games or launch options.
   - **Upgrading from 0.17 or older:** after installing, the plugin shows *"Installed OptiScaler bundle is from an older plugin version"*. Press **Update OptiScaler bundle**, then press **Reinstall** on every patched game so it receives the new injector. Until you do, patching with the Valve RDNA2 runtime is refused on purpose.
2. **Setup OptiScaler**: open the plugin and press "Setup OptiScaler Mod". The default runtime is **4.1.1 | Valve RDNA2 (0.9.4 injector)**, the one verified on a Steam Deck; games patched with it start on FSR 4.1.1 (`Dx12Upscaler=fsr31`, upgraded to FSR 4 by `Fsr4Update`) without opening the overlay. A value you later pick in the overlay is kept on Reinstall. Pressing Setup again on an up-to-date bundle only refreshes scripts and the selected runtime instead of re-extracting everything.
   - The **FSR 4 watermark** toggle shows AMD's FSR 4 label in-game (applied on Patch/Reinstall) so you can confirm the runtime is active.
3. **Patch Games**: pick a title under *Steam game* and press **Patch with dxgi.dll**. The plugin copies OptiScaler into the game folder and sets the Steam launch options for you (`WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%`).
   - "Copy launch options" only re-copies that launch string (for example if Steam lost it); it does not patch anything.
   - Manual Mode exposes the older `~/fgmod` wrapper commands (`~/fgmod/fgmod %command%`, with `DLL=<name>` prepended when a proxy other than dxgi.dll is selected). The wrapper also honours `PRESERVE_INI=false` (re-copy the default INI) and `FGMOD_FSR4_VARIANT=<runtime id>`.
   - The game view has per-game choices, applied when you Patch or Reinstall: **Runtime for this game**, **DX12 upscaler** (runtime default = FSR 3.1 → FSR 4, or XeSS / FSR 2.2 explicitly) and **Frame generation** (the game's own DLSS Frame Generation through Nukem's mod, or OptiScaler's experimental *OptiFG* for games without DLSS FG; OptiFG is game dependent and can glitch the UI).
   - **Copy diagnostics** puts the bundle state, the game's marker, the managed INI keys and the telling `OptiScaler.log` lines on the clipboard (also saved as `~/fgmod/diagnostics-<appid>.txt`). Paste that into an issue instead of describing the problem.
4. **Enable Features**: launch your game and enable DLSS in the graphics settings
5. **Advanced Options**: bind a back button to the keyboard **Insert** key (Steam controller settings) and press it in-game for the OptiScaler overlay

### Removing the Mod from Games
- If you used the in-plugin patcher, select the game and press **Unpatch**. Steam's launch options are restored to what they were before patching.
- If you used the wrapper method, enable Manual Mode and click "Copy Unpatch Command", then replace the launch options with: `~/fgmod/fgmod-uninstaller.sh %command%` and run the game once. After that you can leave the launch option or remove it.
- Files the game shipped under the same names (`libxess*.dll`, `amd_fidelityfx_*.dll`, `dxgi.dll` from ReShade, ...) are kept as `<name>.b` while patched and put back on unpatch. Third-party ASI mods in `plugins/` are left alone; only `OptiPatcher.asi` is removed. A pre-existing manual `OptiScaler.ini` in the game folder is reused (with the plugin's overrides applied) and removed on unpatch.
- Games unpatched by versions up to 0.17 that shipped their own `libxess*.dll` or `libxell.dll` lost those files; use Steam's *Verify integrity of game files* once to get them back. Those versions also renamed a game-shipped `d3dcompiler_47.dll` to `.b` while patched (so it was missing during play) and put it back on unpatch; 0.18 leaves it in place and repairs a leftover `.b`.
- Unpatching from the game view restores the launch options stored when the game was patched. An **Advanced Mode → Unpatch directory** or wrapper uninstall keeps the `FRAMEGEN_PATCH` marker so those options are not lost; use the game view's Unpatch afterwards (or edit the launch options yourself) to hand them back to Steam.
- **Advanced Mode → Unpatch directory** refuses folders that carry no trace of a patch, so it cannot delete a never-patched game's own DLLs.

### Configuring OptiScaler via Environment Variables
As of v0.15.1, you can update OptiScaler settings before a game launches by adding environment variables. 
This is useful if you plan to use the same settings across multiple games so they are pre-configured by the time you launch them.

For example, considering the following sample from the OptiScaler.ini config file:
```
[Upscalers]
Dx11Upscaler=auto
Dx12Upscaler=auto
VulkanUpscaler=auto

[FrameGen]
Enabled=auto
FGInput=auto
FGOutput=auto
DebugView=auto
DrawUIOverFG=auto
```
We can decide to set `Dx12Upscaler=fsr31` to enable FSR4 in DX12 games by default. This works because the option name `Dx12Upscaler` is unique throughout the file but for options that appear multiple times like `Enabled`, you can prefix the option name with the section name like `FrameGen_Enabled=true`.
You can provide section names for all options if you want to be explicit. You can also prefix `Section_Option` with `OptiScaler` to ensure no conflict with other commands.

Here's the breakdown of supported formats:
- `OptiScaler_Section_Option=value` - Full format (foolproof)
- `Section_Option=value` - Short format (recommended)
- `Option=value` - Minimal format (only works if the option name appears once in OptiScaler.ini)

**Example:**
```bash
# Enable frame generation with XeFG output
FrameGen_Enabled=true FGInput=fsrfg FGOutput=xefg ~/fgmod/fgmod %command%

# Set DX12 upscaler to FSR 3.1 (Upgrades to FSR4)
Dx12Upscaler=fsr31 ~/fgmod/fgmod %command%
```

**Notes:**
- Environment variables override the OptiScaler.ini file on each game launch
- Hyphenated section names like `[V-Sync]` can be accessed like `VSync_Option=value`
- If an option name appears in multiple sections of the OptiScaler.ini file, use the `Section_Option` or `OptiScaler_Section_Option` format
- OptiScaler 0.9.4 adds `FSR_Fsr4ForceEnableInt8=true` for the bundled SDK upscaler. It can force INT8 on unsupported GPUs that support INT8, but does not make older non-INT8 hardware compatible and does not affect the `amdxcffx64.dll` driver override. Enable `FSR_Fsr4EnableWatermark=true` to verify the active FSR runtime.

### Choosing an FSR4 Runtime

- **4.1.1 FFX 2.3 SDK**: The upstream 0.9.4 bundled path. Official FSR4 support is RDNA4 (FP8) and RDNA3 desktop GPUs (INT8); it is the only bundled path affected by `Fsr4ForceEnableInt8`.
- **4.1.1 Valve RDNA2 Compatibility**: The Steam Deck / RDNA2 option. It uses the final SDK upscaler with the Valve `amdxcffx64.dll`, `amdxc64.dll`, the OptiScaler v10 nightly injector (2026-09-05 build), and RDNA2-specific INI overrides (`Fsr4ForceModel=2`, `LoadCustomAmdxc64OnRdna2=true`).
  - Versions up to 0.17 shipped a 0.10.0-pre1 injector from 22 June 2026. That build introduced OptiScaler's new menu input system before upstream's Proton fixes landed, so the Insert overlay opened greyed out, could not be clicked, and could not be closed. The 2026-09-05 nightly contains those fixes.
  - The v10 injector no longer reads `ManualInputPolling`; the `Hotfix_ManualInputPolling` env var only affects the other three runtimes.
  - The v10 injector reads the same `OptiScaler.ini` the 0.9.4 runtimes use. It maps `FGInput=nukems` to `FGInput=nvngxfg` + `FGNvngxReplacement=Nukems`, ignores `FGOutput` and `Fsr4Update`, and enables FSR 4 INT8 through `Fsr4ForceModel=2`. When its overlay saves the INI it writes `FGInput=NvngxFG`; the plugin and the wrapper map that back to `nukems` whenever the game is switched to a 0.9.4-based runtime, otherwise frame generation would silently turn off there.
  - On Proton, `amdxc64.dll` is loaded because vkd3d-proton itself calls `LoadLibrary("amdxc64.dll")` on AMD GPUs and Wine prefers the native copy in the game folder; the `LoadCustomAmdxc64OnRdna2` driver-store branch cannot fire under Wine. Watch for the `amdxc64.dll loaded` line in `OptiScaler.log` after Proton updates.
  - To confirm the path is active on a Deck, read `OptiScaler.log` next to the game exe: it must contain `OptiScaler v10.0.0-dev`, `Setting DllPath to <the exe folder>`, a *Detected GPUs* block with `vkd3d-proton: true` and `fsr4: int8 (forced)`, `amdxc64.dll loaded`, `IAmdExtD3DFactory queried, returning custom AmdExtD3DFactory` and `amdxcffx64 loaded from game folder`. With DLSS enabled in the game, the FSR 4 watermark should be visible. If not, fall back to the 4.0.2c runtime.
- **4.1.1 Valve RDNA2 (0.9.4 injector)** *(experimental, added in 0.18.1)*: the same Valve `amdxcffx64.dll` and `amdxc64.dll`, but injected by the bundled OptiScaler 0.9.4 with `Fsr4ForceEnableInt8=true`. 0.9.4's overlay uses the classic WndProc input path, so use this when the v10 overlay opens but ignores the mouse. Not verified on hardware: check the FSR4 watermark; if it stays on FSR3, switch back to the v10 variant or the 4.0.2c runtime.
- **4.1.1 Driver Override**: Uses the same final SDK upscaler plus a separate `amdxcffx64.dll` AMD driver provider. It is a fallback/testing path and is not bundled by upstream 0.9.4.

#### Game-specific notes
- **Red Dead Redemption 2**: FSR 4 only exists for DirectX 12. The game defaults to Vulkan on the Deck, where OptiScaler can only reach FSR 4 through a fragile Vulkan-on-DX12 bridge; switching to it live in the overlay crashes. Set Settings → Graphics → Advanced → **Graphics API = DirectX 12**, choose FSR 2 (or DLSS) in the game with a Quality/Balanced preset (FSR 4 has no Ultra Quality model), then Reinstall from the plugin so the game starts on FSR 3.1 → FSR 4 without touching the overlay. Upstream notes: [RDR2](https://github.com/optiscaler/OptiScaler/wiki/Red-Dead-Redemption-II), [FSR4 compatibility](https://github.com/optiscaler/OptiScaler/wiki/FSR4-Compatibility-List).

#### Overlay opens but nothing is clickable
1. Give the game a mouse: Steam button → Controller Settings → edit the layout → Right Trackpad = **Mouse**, Trackpad Click (or R2) = **Left Mouse Click**.
2. Keyboard navigation works even without a mouse: map D-pad to the keyboard **Arrow keys**, A to **Space**, B to **Escape**.
3. If the mouse still does nothing on the v10 (Valve RDNA2) runtime: the v10 input system only feeds the mouse to the overlay while it believes the game window is the foreground window (keyboard shortcuts bypass that check), and gamescope focus reporting can defeat it. Switch the game to *4.1.1 | Valve RDNA2 (0.9.4 injector)* and press Reinstall, or set the upscaler without the overlay: in the game folder's `OptiScaler.ini` set `Dx12Upscaler=ffx` (v10) or `Dx12Upscaler=fsr31` (0.9.4) under `[Upscalers]`.
4. To diagnose, open the overlay, move the mouse, quit, and look for `OptiInput::LogInputHealthSnapshotLocked` and `SetFocusStateLocked` lines in `OptiScaler.log`: `focused:false` with `foreground:` pointing at another window confirms the focus problem; `focused:true` with `recvWnd:0 rawMouse:0 polledUsed:0` means no mouse reaches the game at all (controller layout).
- **4.0.2c RDNA2/3 Compatibility**: Older compatibility runtime. Prefer the Valve 4.1.1 path for RDNA2 or the regular 4.1.1 driver override when those work for the game.

FSR 4.1.1 can fall back internally to FSR3 on unsupported hardware. Check the FSR4 watermark (`FSR4`, `FSR4-i8`, or `FSR3`) after changing a runtime to confirm the active path.

## Technical Details

### What's Included
- **[OptiScaler 0.9.4](https://github.com/optiscaler/OptiScaler/releases/tag/v0.9.4)**: Official upstream final bundle with the FFX 2.3 SDK / FSR4.1.1. The plugin retains its separately bundled FSR4.0.2c compatibility runtime and existing 4.1.1 driver-override variants; the final upstream archive itself does not include those driver-override DLLs.
- **[OptiScaler v10 nightly (2026-09-05)](https://github.com/optiscaler/OptiScaler-nightly/releases/tag/nightly-20260905)** (build `v10.0.0-dev da70e61e`): Only its root `OptiScaler.dll` is used, as the injector for the Valve RDNA2 runtime. Its FSR upscaler / frame-generation / Vulkan DLLs and the XeSS libraries (`libxess*.dll`) are byte-identical to the 0.9.4 ones already in `~/fgmod`; the nightly's newer `libxell.dll` and `dlssg_to_fsr3_amd_is_better.dll` are not used. Decky downloads it at install time from the dated upstream nightly release; mirroring the byte-identical file on a release the maintainer controls (same SHA-256, only the URL changes) would protect installs if that nightly is ever pruned. `python3 scripts/refresh-injector.py [tag] [--apply]` inspects a newer nightly, verifies the DLL still reads every INI key the plugin sets, and rewrites the hashes in `main.py`, `package.json` and `bin/`; upload the new archive to the mirror afterwards.

### Building from source
`bin/` is not committed (about 360 MB). `python3 scripts/fetch-bin.py` downloads and hash-verifies every binary listed in `package.json`, `pnpm install --frozen-lockfile && pnpm run build` type-checks and bundles the frontend, `python3 -m unittest discover -s tests -t tests -v` runs the backend, script and packaging tests against the real binaries, and `scripts/package.sh` writes the installable `Decky-Framegen.zip`. The `build-zip` GitHub Actions workflow does the same on demand.
- **Nukem9's DLSSG to FSR3 mod**: Allows use of DLSS inputs for FSR frame gen outputs, and xess or FSR upscaling outputs
- **FakeNVAPI**: NVIDIA API emulation for AMD/Intel GPUs, to make DLSS options selectable in game
- **Supporting Libraries**: All required DX12/Vulkan libraries (libxess.dll, amd_fidelityfx, etc.)


## Credits

### Core Technologies
- **[Nukem9](https://github.com/Nukem9/dlssg-to-fsr3)** - Creator of the DLSS to FSR3 mod that makes frame generation possible
- **[Cdozdil/OptiScaler Team](https://github.com/optiscaler/OptiScaler)** - OptiScaler mod that provides the core functionality and bleeding-edge improvements
- **[Artur Graniszewski](https://github.com/artur-graniszewski/DLSS-Enabler)** - DLSS Enabler that allows DLSS features on non-RTX hardware
- **[FakeMichau](https://github.com/FakeMichau)** - Various essential tools including fgmod scripts, innoextract, and fakenvapi for AMD/Intel GPU support

### Community & Documentation
- **[Deck Wizard](https://www.youtube.com/watch?v=o_TkF-Eiq3M)** - Extensive community support including comprehensive guides, promotional content, thorough testing and feedback, custom artworks, and tutorial videos. His passionate advocacy and continuous support have been instrumental in Decky Framegen's success.

- **The DLSS2FSR Community** - Ongoing support and guidance for understanding the various mods and tools
