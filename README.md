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

1. **Install the Plugin**: Download and install through Decky Loader "install from zip" option in developer settings
2. **Setup OptiScaler**: Open the plugin and click "Setup OptiScaler Mod" 
3. **Configure Games**: For each game you want to enhance:
   - Click "Copy Patch Command" in the plugin
   - Go to your game's Properties → Launch Options in Steam
   - Paste the command: `~/fgmod/fgmod %command%`
4. **Enable Features**: Launch your game and enable DLSS in the graphics settings
5. **Advanced Options**: Press the Insert key in-game for additional OptiScaler settings

### Removing the Mod from Games
- Click "Copy Unpatch Command" and replace the launch options with: `~/fgmod/fgmod-uninstaller.sh %command%`
- Run the game at least once to make the uninstaller script run. After you can leave the launch option or remove it

### Configuring OptiScaler via Environment Variables
Starting v0.14.0, you can update OptiScaler settings before a game launches by adding environment variables. 
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

## Technical Details

### What's Included
- **[OptiScaler_v0.7.9](https://github.com/optiscaler/OptiScaler/releases/tag/v0.7.9)**: Latest bleeding-edge build (as of writing), with new features such as OptiFG for adding FG to games without any FG (highly experimental)
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
