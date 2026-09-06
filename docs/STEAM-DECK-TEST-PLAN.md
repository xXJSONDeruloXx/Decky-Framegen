# Steam Deck acceptance test for Decky Framegen v0.18

Everything in this release was verified from source and with automated tests against the
real binaries, but no Steam Deck was available to the author. These steps prove the two
things only hardware can prove: the OptiScaler overlay accepts input under Proton, and FSR 4
INT8 renders on the Deck's RDNA2 GPU. Each step states what you should see.

## 0. Prepare
- Note the Decky Loader version (Decky → gear → About). Must be 3.0.0 or newer.
- Wi-Fi on: the install re-downloads ~360 MB.
- Write down the launch options of the game you will test (Properties → General).

## 1. Install
1. Desktop Mode browser, logged in to GitHub: download `Decky-Framegen.zip` from the release
   page. Keep the file name exactly `Decky-Framegen.zip`.
2. Gaming Mode: Quick Access Menu → Decky → gear → **Developer** (enable *Developer mode*
   under General if the tab is missing) → **Install Plugin from ZIP File** → Browse → the zip →
   confirm.
   - Expected: progress reaches the end after a few minutes; `Decky-Framegen` appears in the
     plugin list. If it ends with *Could not download remote binaries*, restart Decky
     (Settings → General → Restart Decky); the plugin then appears anyway.
3. Desktop terminal:
   ```bash
   ls ~/homebrew/plugins/Decky-Framegen/bin
   sha256sum ~/homebrew/plugins/Decky-Framegen/bin/OptiScaler_v10.0.0-pre1_20260905.7z
   ```
   - Expected: 7 files, no `OptiScaler_0.10.0-pre1.20260622_135940.dll`;
     hash `bc87598d8622ec938089582e88f1689d708a7db76c68dfe415e514c5b13216ed`.

## 2. Bundle
4. Open the Decky Framegen panel. If `~/fgmod` from v0.17 exists you see *Installed OptiScaler
   bundle is from an older plugin version* → press **Update OptiScaler bundle**. Otherwise pick
   *4.1.1 | Valve RDNA2 Compatibility* and press **Setup OptiScaler Mod**.
   - Expected: button shows *Installing OptiScaler...* for 10–60 s, then a green
     *OptiScaler mod installed successfully* line, *Installed bundle: OptiScaler
     0.9.4-final.20260718* with the Valve label, and the runtime dropdown stays on Valve
     (no snap-back within 3 s).
5. Desktop terminal:
   ```bash
   sha256sum ~/fgmod/fsr4-rdna2-valve-411-pre10/OptiScaler.dll ~/fgmod/fsr4-rdna2-valve-411-pre10/renames/dxgi.dll ~/fgmod/OptiScaler.dll
   ```
   - Expected: first two are `c5f06953d91f01593b1e44273dccb76326aa3725f92eb32e7aebe114383e927e`
     (v10 injector), the third differs (0.9.4 injector).

## 3. Patch
6. In the panel: Proxy DLL `dxgi.dll`, Steam game = a DX12 title with a DLSS option (not
   running), press **Patch with dxgi.dll**.
   - Expected: *Patched (dxgi.dll)*, *FSR4 runtime: 4.1.1 | Valve RDNA2 Compatibility*, and
     the game's launch options now read `WINEDLLOVERRIDES=dxgi=n,b SteamDeck=0 %command%`.
7. In the game's exe folder (path shown by the plugin):
   ```bash
   sha256sum dxgi.dll
   grep -nE '^(FGInput|FGOutput|Fsr4ForceModel|LoadCustomAmdxc64OnRdna2|UseHQFont|LoadAsiPlugins)=' OptiScaler.ini
   ls plugins D3D12_Optiscaler
   ```
   - Expected: `c5f06953…`; `nukems`, `nukems`, `2`, `true`, `false`, `true`;
     `plugins/OptiPatcher.asi` and `D3D12_Optiscaler/D3D12Core.dll` present. If the game shipped
     its own `libxess.dll` or `dxgi.dll`, the `.b` copies exist.

## 4. Running-game guard
8. Launch the game, reach the menu, open the Quick Access Menu → Decky Framegen → press
   **Reinstall (dxgi.dll)**.
   - Expected: *Close the game before patching.* and no file changes. Same for Unpatch.

## 5. Overlay (the v0.17 bug)
9. Map a back button (L4/L5/R4/R5) to keyboard *Insert* in the game's controller layout.
   Launch the game, get past the loading screen, press the mapped button.
   - Expected: the OptiScaler window opens with `OptiScaler v10.0.0-dev` in its title,
     dropdowns and checkboxes react to the trackpad cursor and clicks, nothing is greyed out,
     and pressing the button again closes it. (v0.17 behaviour: greyed out, unclickable,
     could not be closed.)

## 6. FSR 4
10. Enable DLSS (any quality) in the game's graphics settings. Look for the AMD *FSR 4*
    watermark in a corner of the frame.
11. Quit and read `OptiScaler.log` in the exe folder. Required lines, in order:
    `OptiScaler v10.0.0-dev` … `da70e61e`; `Setting DllPath to <the exe folder>`;
    a *Detected GPUs* block with `vkd3d-proton: true` and `fsr4: int8 (forced)`;
    `amdxc64.dll loaded`; `IAmdExtD3DFactory queried, returning custom AmdExtD3DFactory`;
    `amdxcffx64 loaded from game folder`.
    - If the watermark or these lines are missing, INT8 was not selected: switch the game
      to *4.0.2c | RDNA2/3 Compatibility* (press Reinstall) and report the log.

## 7. Runtime round-trip
12. Quit the game, change *Default FSR4 runtime* to *4.0.2c | RDNA2/3 Compatibility*.
    - Expected: dropdown stays on the new value; the game row shows *Default is now 4.0.2c …
      Press Reinstall to switch this game.*
13. Press **Reinstall (dxgi.dll)**.
    - Expected: `sha256sum dxgi.dll` now equals `~/fgmod/OptiScaler.dll`; `amdxc64.dll` and
      `amdxcffx64.dll` are gone from the game folder with no `.b` files; `OptiScaler.ini`
      shows `Fsr4ForceModel=auto`, `LoadCustomAmdxc64OnRdna2=false`; if you had saved
      settings from the v10 overlay in step 9, `FGInput=nukems` (not `NvngxFG`).
14. Switch back to the Valve runtime, Reinstall, confirm `dxgi.dll` is `c5f06953…` again.

## 8. Unpatch
15. Quit the game, press **Unpatch**.
    - Expected: *Not patched*; launch options back to what you wrote down in step 0; none of
      `dxgi.dll` (or the game's original restored), `OptiScaler.ini`, `OptiScaler.log`,
      `fakenvapi.*`, `amd_fidelityfx_*`, `libxess*`, `libxell.dll`, `amdxc*.dll`,
      `D3D12_Optiscaler/`, `FRAMEGEN_PATCH` remain; `plugins/` is gone unless it held
      third-party files. Steam's *Verify integrity* should re-acquire 0 files for a game that
      shipped no XeSS/dxgi DLLs.

## 9. Optional
16. Advanced Mode → Select directory → a never-patched game folder → **Unpatch directory**.
    - Expected: *No Framegen/OptiScaler patch found in this directory. Nothing was changed.*
17. `cd ~/homebrew/plugins/Decky-Framegen && python3 -m unittest discover -s tests -t tests -v`
    is not available from the zip (tests are not shipped); clone the repo instead.

## What to send back if something fails
`OptiScaler.log` from the game folder, `/tmp/fgmod-install.log` (wrapper launches only),
`journalctl -t fgmod --since -1h`, and Decky's plugin log
`~/homebrew/logs/Decky-Framegen/`.
