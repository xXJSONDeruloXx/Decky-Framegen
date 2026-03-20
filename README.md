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

That makes the integration:

- non-invasive
- reversible
- per-game
- compatible with Steam launch options and future launcher/runtime style integration

## Current default behavior

The default proxy is:

- `winmm.dll`

The default launch command is:

```bash
OPTISCALER_PROXY=winmm ~/fgmod/fgmod %command%
```

To clean a game's managed prefix manually:

```bash
~/fgmod/fgmod-uninstaller.sh %command%
```

## How to use

1. Install the plugin zip through Decky Loader.
2. Open Decky Framegen.
3. Press **Install Prefix-Managed Runtime**.
4. Enable a game from the **Steam game integration** section, or copy the launch command manually.
5. Launch the game.
6. Press **Insert** in-game to open the OptiScaler menu.

## Steam game integration

The plugin can now manage Steam launch options for a selected installed game.

Enable:

- writes `OPTISCALER_PROXY=winmm ~/fgmod/fgmod %COMMAND%` into Steam launch options

Disable:

- clears Steam launch options
- cleans the managed OptiScaler files from the game's compatdata prefix

## Advanced notes

### Config persistence

`OptiScaler.ini` is stored per game under:

```text
compatdata/<appid>/optiscaler-managed/OptiScaler.ini
```

The runtime copies that INI into `system32` before launch and syncs it back after the game exits, so in-game menu saves persist.

### Proxy override

You can test a different proxy by changing the launch option manually:

```bash
OPTISCALER_PROXY=dxgi ~/fgmod/fgmod %command%
OPTISCALER_PROXY=version ~/fgmod/fgmod %command%
```

Supported values currently include:

- `winmm`
- `dxgi`
- `version`
- `dbghelp`
- `winhttp`
- `wininet`
- `d3d12`

### Environment-driven INI updates

The existing OptiScaler env var patching still works. For example:

```bash
Dx12Upscaler=fsr31 FrameGen_Enabled=true OPTISCALER_PROXY=winmm ~/fgmod/fgmod %command%
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
