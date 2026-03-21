# Decky Framegen

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/B0B71HZTAX)

Decky Framegen now treats OptiScaler as a **prefix-managed per-game runtime** instead of a game-folder mod installer.

## What changed

The plugin no longer needs to copy OptiScaler into the game install directory.

Instead, it:

- installs a shared OptiScaler runtime under `~/fgmod`
- stages OptiScaler into `compatdata/<appid>/pfx/drive_c/windows/system32` at launch time
- keeps a writable per-game config under `compatdata/<appid>/optiscaler-managed`
- restores the original Wine/Proton proxy DLL on cleanup
- lets you edit per-game OptiScaler settings from the plugin UI
- can mirror INI changes into the live prefix copy while the game is running

That makes the integration:

- non-invasive
- reversible
- per-game
- much closer to a launcher/runtime feature than a file-drop mod installer

## Current default behavior

The default proxy is:

- `winmm.dll`

The default launch command is:

```bash
~/fgmod/fgmod %command%
```

To clean a game's managed prefix manually:

```bash
~/fgmod/fgmod-uninstaller.sh %command%
```

## How to use

1. Install the plugin zip through Decky Loader.
2. Open Decky Framegen.
3. Press **Install Prefix-Managed Runtime**.
4. Enable a game from the **Steam game integration + live config** section, or copy the launch command manually.
5. Launch the game.
6. Press **Insert** in-game to open the OptiScaler menu.

## Steam game integration + live config

The plugin can now:

- detect the current running game from Steam UI
- pick any installed Steam game from a dropdown
- enable the generic prefix-managed launch option automatically
- disable a game and clean its compatdata-managed OptiScaler state
- read the selected game's managed or live `OptiScaler.ini`
- persist per-game proxy preference
- update quick OptiScaler settings from the plugin UI
- save the full raw `OptiScaler.ini`
- push config changes into the currently staged live prefix copy while the game is running

Enable writes this launch option:

```bash
~/fgmod/fgmod %COMMAND%
```

The wrapper then resolves the proxy using this order:

1. `OPTISCALER_PROXY` / `DLL` environment override if provided
2. saved per-game preferred proxy from `manifest.env`
3. fallback default `winmm`

## Config persistence

Per-game config lives here:

```text
compatdata/<appid>/optiscaler-managed/OptiScaler.ini
```

During launch the wrapper copies that INI into:

```text
compatdata/<appid>/pfx/drive_c/windows/system32/OptiScaler.ini
```

When the game exits, the staged INI is synced back to the managed location.

## Live editing caveat

The plugin can write directly into the live prefix INI while the game is running.

That means:

- the file is updated immediately
- persistence is preserved
- some settings may still require OptiScaler or the game to reload/relaunch before they fully take effect, depending on what OptiScaler hot-reloads internally

In other words: **live file update is supported**, but **live behavioral reload depends on OptiScaler/game behavior**.

## Supported proxy values

- `winmm`
- `dxgi`
- `version`
- `dbghelp`
- `winhttp`
- `wininet`
- `d3d12`

## Environment-driven INI updates

The wrapper still supports environment-based INI overrides. Example:

```bash
Dx12Upscaler=fsr31 FrameGen_Enabled=true ~/fgmod/fgmod %command%
```

## Technical summary

At launch the runtime:

1. resolves `STEAM_COMPAT_DATA_PATH`
2. creates `compatdata/<appid>/optiscaler-managed`
3. preserves the original selected proxy DLL as `<proxy>-original.dll`
4. stages OptiScaler and helper DLLs into prefix `system32`
5. sets `WINEDLLOVERRIDES=<proxy>=n,b`
6. launches the game
7. syncs `OptiScaler.ini` back to the managed directory on exit

## Build notes

Local frontend build:

```bash
pnpm build
```

Decky zip build:

```bash
bash .vscode/build.sh
```

If Decky CLI is missing, run:

```bash
bash .vscode/setup.sh
```

## Credits

- [Nukem9](https://github.com/Nukem9/dlssg-to-fsr3)
- [OptiScaler / cdozdil](https://github.com/optiscaler/OptiScaler)
- [Artur Graniszewski / DLSS Enabler](https://github.com/artur-graniszewski/DLSS-Enabler)
- [FakeMichau](https://github.com/FakeMichau)
- Deck Wizard and the DLSS2FSR community
