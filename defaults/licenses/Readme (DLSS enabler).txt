DLSS Frame Generation enabler package v3.02.000.0
===============================================================================================================================

INTRODCTION:
--------------------------------------------------------------
This all-in-one package allows the users of any DX12 compatible GPUs (from NVIDIA/AMD/Intel) to enable DLSS upscaler and DLSSG Frame Generation in most of the games implementing NVIDIA DLSS 2 / DLSS 3 features.


WHAT'S INCLUDED:
--------------------------------------------------------------
1) DLSS enabler DLL version 3.02.000.0

2) Nukem9 DLSSG to FSR3 mod version 0.110

3) Optiscaler mod version 0.6.7.11

4) (optional) NVIDIA Runtime Environment for AMD and INTEL ARC GPUs, version 3.02.000.0 (containing DXGI proxy and FakeNVAPI in version 1.0.3.0)



CREDITS:
--------------------------------------------------------------
DLSS enabler DLL is based on DLSSSpoofer from NitroG0d: https://github.com/nitrog0d/DLSSSpoofer

DLSS enabler DLL depends on DLSSG to FSR3 mod from NUkem9: https://github.com/Nukem9/dlssg-to-fsr3 and https://www.nexusmods.com/site/mods/738?tab=files

DLSS enabler Installator for AMD/Intel GPUs depends on FakeNVAPI project by FakeMichau: https://github.com/FakeMichau/fakenvapi

DLSS enabler Installator for AMD/Intel GPUs depends on DX12 proxy by Nitec: https://github.com/cdozdil/d3d12-proxy/releases/tag/v0.1

DLSS enabler DLSS upscaler emulation depends on Optiscaler by Nitec: https://github.com/cdozdil/OptiScaler


SUPPORTED GPUs:
--------------------------------------------------------------
NVIDIA GeForce 20xx/30xx (full support)
NVIDIA GeForce 10xx/16xx (good support)
NVIDIA GeForce 9xx (good support)
NVIDIA GeForce 8xx (experimental)
INTEL ARC (good support)
AMD RDNA3 (full support)
AMD RDNA2 (good support)
older GPUs (good/limited support)


GAMES TESTED:
--------------------------------------------------------------
You can find the complete list of tested games here: https://docs.google.com/spreadsheets/d/1qsvM0uRW-RgAYsOVprDWK2sjCqHnd_1teYAx00_TwUY/edit?usp=sharing


TROUBLESHOOTING
--------------------------------------------------------------
You can use the following commandline arguments to troubleshoot your game:

 --dlss-debug           - shows the debug console in the background
 --dlss-debug=extra     - shows extensive debug information in a debug console
 --dlss-logging=on/off  - enables logging to the file (default: off)
 --dlss-version         - reports the DLL version used to enable DLSS Frame Generation
 --dlss-upscaler=auto/fsr/xess/dlss - allows to select default DLSS upscaler implementation/emulation, (default: auto = XeSS for non RTX cards/DLSS for RTX cards)
 --dlss-upscaler-quality=sys/ultra - ultra setting forces XeSS/FSR upscalers to render in native resolution only (default: sys - use generic quality profiles) 
 --dlss-hags=on/off/sys - enables/disables or uses system setting for Hardware Accelerated GPU Scheduling even on unsupported hardware/drivers (default: on)
 --dlss-help            - shows the help message with all the arguments supported by the DLL
 --dlss-arch=ZZZ        - allows to spoof different NVIDIA GPU architecture, possible choices: ada (default, if argument not present), turing, ampere, ie --dlss-arch=ampere
 --dlss-disable         - disables the DLL functionality
 --dlss-skip-validation - skips system checks (that are validating HAGS, NVIDIA signature checking or presence of FSR3 files)
 --dlss-diagnostics     - Shows the mod diagnostics
 --dlss-nvapi=mock/proxy/sys - Controls which Nvidia API interface to use (default: proxy).
 --dlss-reflex-fps=ZZZ  - Enables frame rate limiter (default: no limit), where ZZZ is a number of target frames per second (including generated ones)
 --dlss-gpu-name="ZZZ"  - Overrides the name of the GPU reported to the application (default: none = use original GPU name), available only when AMD/Intel compatibility package is installed.
 --dlss-gpu-vram=32g    - Overrides the amount of GPU RAM reported to the application (available only after installing AMD/INTEL support package), can be set to any value between 1 and 128 gigabytes
for additional info).



EXAMPLES:
--------------------------------------------------------------
1) Check if DLLS enabler is installed successfully (shows a pop-up with its version and closes the game on start):
    
   "C:\Games\The Witcher 3 Wild Hunt GOTY\bin\x64_dx12\dlss-enabler.exe" witcher3.exe --dlss-debug=extra

2) Run Witcher 3 with debug console enabled:

   "C:\Games\The Witcher 3 Wild Hunt GOTY\bin\x64_dx12\dlss-enabler.exe" witcher3.exe --dlss-debug=extra

3) Run Cyberpunk 2077 with Cyber Engine Tweaks present in its x64 directory:

   "C:\Games\Cyberpunk 2077\bin\x64\dlss-enabler.exe" cyberpunk2077.exe

4) Run Witcher 3 with DLLS enabler spoofing ampere GPU:

   "C:\Games\Cyberpunk 2077\bin\x64\dlss-enabler.exe" cyberpunk2077.exe --dlss-arch=ampere


KNOWN ISSUES/LIMITATIONS:
--------------------------------------------------------------
1) Problem: Vignette shaking when quickly moving the camera up/down or left/right in Cyberpunk
   Solution: Install two mods disabling vignette when crouching and during the normal movement. If necessary enable vignette feature provided by NVIDIA overlay (filter options under Alt+F3 shortcut)

2) Problem: Ghosting of moving objects
   Solution: Ghosting needs to be expected from FSR3 Frame Generation feature. You can reduce its visibility by increasing the host FPS, in order to do so, enable image upscaling, or if its enabled - reduce its quality and/or reduce the graphics settings in general. Please note that upscalers introduce their own ghosting (XeSS technique in particular), so choose wisely and experiment.

3) Problem: Frame generation blocks the in-game V-Sync option and sets it to off
   Solution: Open NVIDIA control panel, and force V-Sync option there, pick either "adaptive" or "fast" option to reduce the V-Sync latency

4) Problem: Camera lag noticeable when moving or looking around
   Solution: Latency can be reduced by increasing the number of host frames generated by your GPU, see solution to a "Ghosting of moving objects".

5) Problem: After playing the game for few minutes Frame Generation feature disables itself for no reason/Frame Generation option is on, but the game is unstable
   Solution: Update your game to the latest version and try again, if issue persist, try to troubleshoot it with --dlss-debug command or report the issue on Discord channel

6) Problem: I want to use Steam/Good Old Games/Epic Megastore client to run the game
   Solution: Try to install the preferred solution (based on DLL file) first and check if it works. Universal solution should be used only if the preferred one is not working as it's less compatible with external game launchers, though more compatible with the games started directly.

7) Problem: There version of nukem9 mod bundled with this installer is outdated, how to install the latest one?
   Solution: Download the ZIP package with the latest version of nukem9 mod and copy paste the DLL files into the game directory where the game executable is. DLLS enabler will detect these files and use them instead of the bundled version.

8) Problem: I want to install the DLL version of the mod, but there's already a file called "version.dll" in my game directory that is not part of this package. What to do?
   Solution: You can either rename it to version-original.dll before installing the mod, or if this fails (the game doesn't start after installation, or reports any other error), you can try to se the universal solution, or uninstall the mod that delivered the original version.dll file.

9) Problem: My game behaves weird/doesn't start/Frame Generation setting cannot be enabled
    Solution: Make sure you didn't install any other mods that try to enable Frame Generation feature (like LukeFZ mod or dummy nvapi64.dll file). If so, revert these changes before installing DLSS enabler. Additionally, make sure your game is up to date (you are running the latest version of the game), as the old versions tend to not to be able to detect Frame Generation capability or be unstable with Frame Generation on.

10) Problem: Original nukem9 mod requires me to disable NVIDIA Driver Signature Checks, is it also true in case of this installation?
    Solution: No, in case of this installation Frame Generation mechanism will work even with Signature Checks on. Please DO NOT disable them unless its really required as part of troubleshooting process.

11) Problem: I want to troubleshoot some issue with this mod, how to do this?
    Solution: After starting the game hit a combination of Ctrl+` (Control + Tilde) twice to spawn a debug console. You can close it and spawn it again afterwards by hitting the same keys again.

12) Problem: DLLS Enabler reports that Hardware Accelerated GPU Scheduling (HAGS) is not supported by Windows Driver
    Solution: Update your GPU drivers to the latest version, or if you're using an older AMD GPU, consider installing custom/community drivers with Hardware Accetelared GPU Scheduling enabled. If your GPU driver doesn't support HAGS at all, start the game with --dlss-hags=on and --dlss-skip-validation commandline arguments to simulate HAGS functionality in DLSS Enabler.

13) Problem: I'm an AMD/Intel GPU owner and after installing NVIDIA Runtime Environment package Ray Tracing no longer works in my game
    Solution: For now, DLSS Enabler is in conflict with RT capabilities, to restore RT capability, you need to uninstall the DLSS Enabler mod and forget about Frame Generation feature.

   

CHANGELOG:
--------------------------------------------------------------
3.02.000.0:
  - Feature: Reduced system latency on AMD RDNA 1+ GPUs with and without Frame Generation enabled (by using AntiLag2 provided by FakeNVAPI)
  - Feature: Reduced system latency on INTEL ARC GPUs and AMD pre RDNA1 GPUS with and without Frame Generation enabled (by using LatencyFlex provided by FakeNVAPI)
  - Feature: Reduced system latency on NVIDIA 8xx+ GPUs with and without Frame Generation enabled (by using native Reflex feature from NVIDIA drivers)
  - Feature: Changed how the ini setting "ReflexEmulation" works - from now on "auto"/"off" will enable AntiLag2 and LatencyFlex on GPUs that do not support Reflex, while "on" will disable AL2 and LFX
  - Feature: Updated OptiScaler to version 0.6.7 (providing new features like VRAM size spoofing, FSR 3.1 upscaler for DX11 games and improving overall stability of itself and DLSS Enabler)
  - Feature: Updated FakeNVAPI module by FakeMichau to version 1.0.3 (improved support for "TLoU 1" and Vulkan API additions, AntiLag2 and LatencyFlex features, improved FPS limiter)
  - Feature: Improved integration with OptiScaler (menu should be available even without DLSS upscaler enabled, changed the default OverlayMenu setting to true)
  - Feature: Improved support for Vulkan in OptiScaler and DLSS Enabler (DLSS Enabler can negotiate upscaler backend with OptiScaler)
  - Feature: Implemented VSYNC feature for DirectX Games (working with Frame Generation enabled), can be enabled in nvngx.ini file (FramerateLimit=vsync)
  - Feature: DLSS Enabler can be installed as a dbghelp.dll file, which increases the success chance of enabling Frame Generation in more problematic games.
  - Feature: Improved selection of GPU to render the game images (DLSS Enabler will prefer the GPU with largest VRAM available)
  - Feature: Enabled experimental support for Vulkan games under Windows (for now enabling DLSS upscaling only)
  - Feature: Support for Vulkan games under Linux is disabled by default, but can be enabled by changing "Vulkan" setting in nvngx.ini file from auto to true 
  - Feature: Improved support for DirectX 11 games (enabling DLSS upscaling only)
  - Feature: Added support for "Rise of the Tomb Rider" (enabling DLSS upscaling)
  - Feature: Added support for "Baldur's Gate 3" in Vulkan mode (enabling DLSS upscaling)
  - Feature: Added support for "Doom Eternal" (enabling DLSS upscaling on GTX 10XX/16XX cards, no AMD/INTEL support yet)
  - Feature: Added limited support for "No Man's Sky" (enabling DLSS upscaling and Frame Generation on RTX and GTX 16XX cards)
  - Feature: Improved compatibility with "Destroy All Humans 2 Reprobed" (addressed disco lights in DLSS mode)
  - Feature: Added support for "Black Myth Wukong Benchmark Tool" under Windows and Linux
  - Feature: Improved integration with future versions of OptiScaler (enabling future improvements in OptiScaler's compatibility with various games)
  - Feature: Heavy code refactoring (to be continued in further beta releases)
  - Feature: Improved Hardware Accelerated GPU Scheduling spoofing under Linux/SteamOS
  - Feature: Added DeepDVC spoofing on unsupported hardware (NVIDIA GTX, AMD, INTEL), can be controlled with [Spoofing]DeepDVC=auto|true|false (auto = true) ini setting
  - Feature: Added very basic emulation of Reflex API in Vulkan games for non-NVIDIA GPUs
  - Bugfix: Fixed CTD on game shutdown in "Witcher 3" (updated OptiScaler)
  - Bugfix: Warning messages about outdated GPU drivers should no longer appear in Nixxes games (updated OptiScaler configuration).
  - Bugfix: Fixed CTD in "The Last of Us Part 1" when game initializes itself
  - Bugfix: Fixed VSYNC option being disabled silently when alt-tabbing between windows, or when enabling/disabling Frame Generation option in the game settings
  - Bugfix: Fixed the log entry about successful loading of DLSS upscaler backend being reported as error, rather than information
  - Bugfix: Fixed CTD in "GoW:Ragnarok" when game tries to use DLSS upscaling
  - Bugfix: Fixed potential instability when using RTSS Overlay and alt-tabbing or launching the game (fix provided by OptiScaler)
  - Bugfix: Fixed game crashes when using SpecialK overlay
  - Bugfix: Fixed lack of Reflex option in SpecialK overlay for NVIDIA, AMD and INTEL GPUs

3.01.000.0:
  - Feature: Added support for selectable FSR 3.0/FSR 3.1 Frame Generator (through ini file and --dlss-fg=fsr30/--dlss-fg=fsr31 commandline arguments)
  - Feature: Added support for FSR 3.1 upscaler (updated OpiScaler to version 0.6.5)
  - Feature: Updated DLSSG-to-FSR3 mod by Nukem to the latest version with better support for Vulkan games
  - Feature: Updated XeSS to version 1.3.1
  - Feature: Feature: General game compatibility improvements (unlocking DLSS in games like Lego Builder, Tomb Raider…) by deploying nvngx.dll file rather than _nvngx.dll file
  - Feature: Extended DLSS Enabler's API (GetFrameGenerationMode/SetFrameGenerationMode) to give the control over Dynamic Frame Generation feature
  - Feature: Improved compatibility (no more driver warnings or errors about missing display device) on AMD/Intel cards with:
    - Rift Apart
    - Horizon Forbidden West
    - Ghost Of Tsushima
    - Miles Morales
    - Spiderman Remastered
  - Feature: Added optional installation option for SteamOS and Linux users that spoofs the RTX GPU on DXVK level (usable in games not listed above, that warn about missing GPU or outdated drivers)
  - Feature: Enabling Reflex Emulation in Horizon Zero Dawn which improves frame pacing and frametimes stability on AMD/INTEL GPUs when using Optiscaler or Frame Generation provided by DLSS Enabler
  - Feature: Updated NVAPI64 proxy from FakeMichau to the latest version (reducing the file size considerably)
  - Feature: Improved awareness of crash reporting process spawned by Unity Engine, so DLSS Enabler no longer tries to enable DLSS in it anymore
  - Feature: Improved compatibility with Bright Memory: Infinity (addressed disco lights in DLSS mode and switching back to FSR 3.0 Frame Generation)
  - Feature: Improved compatibility with Ready or Not (addressed disco lights in DLSS mode and potential CTDs when enabling Frame Generation)

3.00.000.0:
  - Feature: Updated Frame Generation from FSR3.0 to FSR3.1 (comes shipped with Nukem mod from version 0.100).
  - Feature: Added future support for FSR3.1 upscaler which will be implemented by Optiscaler mod (Optiscaler supporting FSR3.1 is not shipped yet)
  - Feature: Updated NVAPI64 proxy from FakeMichau to the latest version (which disables logging NVAPI calls by default)

2.90.802.0:
  - Feature: Added support for Frame Generation on all GPUs in games implementing DLSS Frame Generation through very old Streamline v1 library (ie Dying Light 2)
  - Bugfix: Addressed race condition when spoofing Hardware Accelerated GPU Scheduling under Linux/SteamOS

2.90.801.0:
  - Bugfix: Fixed CTD on AMD/INTEL GPUs in Cyberpunk 2077 edition of DLSS Enabler

2.90.800.0:
  - Feature: Added compatibility with DLSS 3.7.x on AMD and INTEL GPUs
  - Feature: Registry keys that disable NVIDIA signature checks are no longer needed on AMD and INTEL GPUs after installing the mod using DLSS Enabler's setup application 
  - Feature: Is shipped with Optiscaler module 0.6.1.22
  - Feature: Optiscaler module 0.6.1.22 allows to configure XeSS, FSR and DLSS during the game when using DLSS upscaler option (hit "Insert" button to open the UI)
  - Feature: Frame Limiting feature can be now controlled from Optiscaler UI.
  - Feature: (Tech Preview/Experimental) "Dynamic Frame Generation" can be now controlled (enabled/disabled) from Optiscaler UI.
  - Feature: Basic framerate stabilization mechanism for AMD/INTEL GPUs is now toggable in nvngx.ini file (and disabled by default), see "ReflexEmulation=auto"
  - Feature: Exposed additional API to third party mods that give them control over Frame Generation feature (usable in game specific mods)
  - Feature: Added compatibility with DLSS 3.7+. Installer is now able to circumvent restrictions related to NVIDIA signature checks when installing AMD/INTEL support package
  - Feature: Various code optimizations and refactoring resulting in much smaller binary files and a bit improved stability/performance
  - Feature: Improved awareness of crash reporting processes spawned by games, so DLSS Enabler no longer tries to enable DLSS in them for no reason
  - Feature: Added new installation option to setup application allowing to install DLSS Enabler as a dxgi.dll file (compatible with DLSS Enabler 2077 edition for Cyberpunk)
  - Feature: Added more selective spoofing of Hardware Accelerated GPU Scheduling (activating itself only when HAGS is not already supported)
  - Feature: Improved logging capabilities and log readability
  - Bugfix: Improved compatibility with SpecialK on NVIDIA GPUs (as long as DLSS Enabler is not installing its own dxgi.dll file)
  - Bugfix: Fixed CTD when Dx12Upscaler is set to dlss (bug introduced in 2.90.750.0)
  - Bugfix: Fixed CTD in Banishers happening during game's shutdown
  - Bugfix: Fixed OptiScaler logs not being sent to DLSS Enabler
  - Bugfix: Fixed CTD on RTX cards when using Ray Reconstruction (bug introduced in 2.90.750.0)
  - Bugfix: Improved compatibility with Jedi Survivor
  - Bugfix: Fixed rare CTD in NVAPI mocking code

2.90.750.0:
  - Feature: Added compatibility with Optiscaler 0.5+
  - Feature: Is shipped with Optiscaler module 0.5.6-pre2
  - Feature: Implemented frame rate limiter feature controlled with new commandline argument --dlss-reflex-fps=XX (where XX is the amount of target FPS) or ini setting "FramerateLimit"
  - Feature: Frame rate limiter can be configured realtime in Optiscaler options window.
  - Feature: Implemented basic framerate stabilization mechanism on non NVIDIA GPUs (which should reduce the jitter/stuttering)
  - Feature: Delegating DLSS upscaler calls to Optiscaler if its in version 0.5.0+ (in case of version 0.4 DLSS Enabler is still responsible for handling native DLSS calls)
  - Feature: (Tech Preview/Experimental) Implemented "Dynamic Frame Generation" feature controlled with commandline arguments --dlss-fg-mode=dynamic --dlss-reflex-fps=XX, where XX is the minimum FPS above which DLSS Enabler will disable or enable Frame Generation

2.90.700.0:
  - Feature: Fix for UI glitches happening exclusively on AMD RDNA2 cards in Cyberpunk 2077 (caused by a bug in game's engine)
  - Feature: Extended logging capabilities (--dlss-debug=ultra commandline argument), ability to log DXGI operations
  - Feature: Ability to load the mod through dxgi.dll file provided by the installer (rather than relying on version.dll or winmm.dll)
  - Feature: Is shipped with Optiscaler module 0.4.3
  - Feature: Dedicated integration with Optiscaler (ability to log the Optiscaler operations, override upscaler settings on DLSS Enabler level, etc)
  - Feature: Ability to load the DLSS Enabler mod files from outside of the game directory
  - Feature: Disabled Ray Reconstruction feature on unsupported hardware (to avoid application crashes)
  - Feature: (for NVIDIA GPUs) Disabling NVIDIA Reflex under Linux/Wine 9 due to a bug in dxvk-nvapi library which caused dramatic FPS drops after enabling Frame Generation
  - Feature: Introduced detection of concurrent (conflicting) installations of DLSS Enabler module, which will protect the games from unexpected crashes
  - Bugfix: Fixed Wine 9/Wine 8 version detection under Linux
  - Bugfix: Fixed streamline loader under Linux (solving error code: 126)
  - Bugfix: (for NVIDIA GPUs) Fixed GPU architecture detection under Linux/Wine 9 (which reported Pascal architecture in case of RTX Turing GPUs)
  - Bugfix: Fixed missing log entry reporting resolution for native DLSS upscaler
  - Bugfix: Fixed compatibility with streamline_sample (which defaulted to Microsoft Software Renderer)
  - Bugfix: Fixed potential incompatibility with more obscure DLSS/DLSSG integrations in games
  - Bugfix: Improved handling of unsupported Mosaic, SLI and Stereo features on AMD/Intel GPUs
 
2.90.606.6:
  - Feature: Improved general compatibility and performance with all Unreal Engine 5 games (switching from XeSS to FSR in auto mode)
  - Feature: Improved compatibility (switching from XeSS to FSR in auto mode) with:
    - Banishers Ghosts of new Eden
    - Fort Solis
    - Immortals of Aveum
    - Lords of The Fallen (2023)
    - Remnant 2
    - RoboCop - Rogue City
  - Feature: Improved compatibility with Dragons Dogma 2 (fixed missing UI elements in FSR mode by switching to XeSS):
  - Feature: Improved integration with the upcoming OmniScaler 0.4 module (0.4 mod will be included in the further releases)
  - Bugfix: Fixed proxy error 5 in Forza Horizon 5
  - Bugfix: Fixed NVIDIA Mosaic feature on NVIDIA GPUs

2.90.606.5:
  - Feature: Updated XeSS backend from 1.2 to version 1.3
  - Feature: Increased general compatibility with some Unreal Engine 4 games
  - Bugfix: Fixed compatibility (crash to desktop bug) with:
    - Kena: Bridge of Spirits
    - Ghostrunner 2

2.90.606.4
  - Feature: Various performance improvements, especially for weaker CPUs (your mileage may vary, do not expect more than 5% improvement)
  - Feature: Installer provides an option to edit the nvngx.ini file after an installation
  - Feature: Autoconfiguration detects Unreal Engine 5 games and switches from XeSS to FSR to avoid visual artifacts
  - Feature: Improved compatibility (no more driver warnings) on AMD/Intel cards with:
    - Alan Wake 2
    - Banishers Ghosts of new Eden
    - Hogwarts Legacy
    - Immortals of Aveum
    - Lords of The Fallen (2023)
    - Remnant 2
    - RoboCop - Rogue City
    - Starfield
  - Feature: Improved compatibility with Dragons Dogma 2 (relying on XeSS upscaler rather than FSR2)
  - Feature: Additional installation option added: install module under "winmm.dll" filename (giving three potential choices: version.dll, winmm.dll, dlss-enabler.asi)
  - Feature: Experimental --dlss-reflex=boost commandline argument and Reflex=boost nvngx.ini configuration setting, enabling reflex boost even if game UI doesn't provide said option.
  - Feature: Installer should now delete obsolete mod files from previous versions during the mod update
  - Feature: Installer should now drop the uninstall.exe file to game directory (without registering it in Add/remove application control panel)
  - Bugfix: When DLSS Enabler was installed as an ASI module, it couldn't find the nvngx.ini file and in result no default upscaler has been selected when starting the mod
  - Bugfix: Fixed integration with bundled dxgi.dll file from AMD/Intel support package, which may XeSS library to select XMX code path on Intel Arc 

2.90.606.3
  - Bugfix: Version 2.90.606.2 opened debug console by default (it should be hidden now).

2.90.606.2:
  - Feature: Introduction of auto-configuration which tries to select most optimal upscaler backend for the given GPU
  - Feature: Updated CyberXess package to 0.3.3 (plus dedicated integration with that mod)
  - Feature: Added support for nvngx.ini file settings
  - Feature: Passing engine type used by the game to CyberXess so it can tweak its settings based on that information
  - Feature: More sophisticated DLSS unlocking mechanism
  - Feature: Added support for Way of the Hunter (UE4 game).
  - Bugfix: Fixed Crash to Desktop when Hardware Accelerated GPU Scheduling is disabled in Windows Control Panel.
  - Bugfix: Fixed ASI loader support
  - Bugfix: Fixed --dlss-upscaler-quality=ultra in CyberFSR

2.90.606.1
  - Bufix: Installer from 2.90.606 deployed obsolete mod file from 605.9 instead of 606 build.

2.90.606

  - Feature: Official support for Linux/Wine9 (for Upscaling and Frame Generation feature) and Wine8 (for Upscaling only)
  - Feature: Reintroduced support for all RTX cards (you no longer need to stick to 2.90.402 build)
  - Feature: You can now specify native DLSS as your upscaler (using --dlss-upscaler=dlss option), please do not try this on non RTX card
  - Feature: --dlss-upscaler-quality=ultra now works for every upscaler (DLSS/CyberXess/CyberFSR), it renders at full display resolution when using Quality DLSS mode
  - Feature: From now on autodetection mechanism defaults to DLSS upscaler on RTX cards, while selecting XeSS for anything else (GTX included)
  - Feature: Additional --dlss-fg=dlssg switch disabling FSR3 upscaler and enabling DLSS-G instead (works only on RTX 40XX cards)
  - Feature: Improved --dlss-nvapi=mock feature (10 additional functions mocked).
  - Feature: Updated CyberXess module (improving image quality and configurability using nvngx.ini file)
  - Bugfix: Better compatibility with Reshade (you no longer need to rename dxgi.dll file provided by reshade if you're not relying on AMD/Intel support package)
  - Bugfix: Installer now deploys the ASI file into the plugins subdirectory when installing DLSS Enabler as an ASI module.

2.90.605.9
  - Bugfix: Fixed Ray Tracing on non RTX cards

2.90.605.8
  - Bugfix: Fixed CTD in DXGI.dll module that is part of AMD/Intel support package

2.90.605.7
  - Bugfix: Fixed the issue where ZIP archive couldn't be unpacked under Windows Explorer (due to incompatible compression algorithm used by 7-zip).
  - Bugfix: Fixed the issue where ZIP archive for GTX users containing nvapi64-proxy.dll from AMD/Intel support package, that impaired mod performance on GTX cards (file has been removed from GTX package).

2.90.605.6
  - Bugfix: Fixed poor image quality produced by CyberFSR module in DLSS mode
  - Bugfix: Fixed DLSS upscaler option disabled in some UE5 games like Hogwarts Legacy when using CyberFSR as a DLSS upscaler

2.90.605.5
  - Bugfix: Fixed error message appearing when dlss-enabler.exe in universal mode is used to start the game (for Windows build).

2.90.605.4
  - Bugfix: Fixed error message appearing when dlss-enabler.exe in universal mode is used to start the game (for Linux build).

2.90.605.3
  - Feature: Experimental support for Wine 9 under Linux (enables Frame Generation and DLSS upscaler)
  - Feature: Very limited support for Wine 8 under Linux (enables DLSS upscaler only)

2.90.605.2
  - Bugfix: Installer no longer uninstalls libxess.dll from game directory (in case a version provided by the game has been there before)

2.90.605
  - Feature: Added spoofing of VRAM (--dlss-gpu-vram=128G), supported only after installing AMD/INTEL support package
  - Feature: Added DLAA quality setting to CyberFSR and CyberXess
  - Feature: DLSS Enabler can be installed as an ASI plugin
  - Bugfix: Potential fix for XeSS performance regression on INTEL ARC GPUs

2.90.604 codename "Imperio curse"
  - Feature: Native integration with the latest CyberXess (version 0.2) module provided by Nitec
  - Feature: Contains the latest CyberXess build from Nitec, and --dlss-upscaler=auto defaults to CyberXess from now on (not FSR anymore)
  - Feature: DLSS Enabler will start with --dlss-nvngx=proxy attribute by default on all kinds of GPUs, NVIDIA included (can be overriden by --dlss-nvngx=sys)
  - Bugfix: Improved DLSS FG unlocking mechanism (hopefully on par with build 500 and 601) that has been a bit broken in 602/603 builds
  - Bugfix: Some race conditions removed
  - Bugfix: Yet another nvngx proxy refactoring

2.90.603
  - Internal release

2.90.602 
  - Feature: CyberFSR/CyberXess upscalers stability improvements (based on custom fork of the said mods)

2.90.601 codename: "Horcrux"
  - Feature: Fully functional, built-in _NVNGX.dll replacement for non-NVIDIA GPU owners (original file is still needed to pass the streamline signature checks)

2.90.600 codename: "DLSS alohamora"
  - Feature: Stable CyberFSR integration
  - Feature: Stable CyberXess integration
  - Feature: Fully selectable DLSS emulation: FSR/XeSS for non RTX cards (--dlss-upscaler=auto/fsr/xess/dlss/off switch)
  - Feature: More advanced/additional spoofing mechanisms for more problematic games
  - Feature: Automatic detection of the most optimal upscaler emulation to use for non RTX cards
  - Feature: Heavy refactoring of low level mod APIs enabling further integrations with other mods
  - Feature: Ultra quality mod available to XeSS/FSR upscalers (--dlss-upscaler-quality=ultra), forcing them to render in native resolution
  - Feature: Logging to file is now possible (--dlss-logging=on/off switch)
  - Feature: Fully customizable GPU name reported to the application (--dlss-gpu-name="3dfx Voodoo2 SLI"), for now available only when AMD/Intel support package is installed
  - Feature: After installing AMD/INTEL support package, DLSS enabler no longer reports hardcoded "Nvidia GeForce RTX 4090" GPU name to the application, instead it provides the actual GPU names instead
  - Feature: Customizable NV API integration (--dlss-nvapi=mock/proxy/sys, default: proxy), "mock" value is experimental but is able to speed up the game initialization by up to 50% in comparison to version 2.90.400.
  - Feature: DXGI.dll file deployed as part of AMD/INTEL support package is able to proxy the calls to dxgi-original.dll file if it exists in the same directory (usable in case of clash with other mods)
  - Bugfix: DLSS Enable no longer creates empty dlssg_to_fsr3.log file when starting the game
  - Bugfix: Improved compatibility with Dying Light 2 (fixed regression introduced in 2.90.500 build)


2.90.502 (internal discord release)
  - Feature: Experimental CyberXess integration
  - Bugfix: Improved (but still experimental) CyberFSR integration

2.90.500 codename: "protego totalum" (internal discord release)
  - Feature: DLSS Enabler is now able to protect its critical files against unload attempts performed by some anti-cheating game mechanisms
  - Feature: Experimental CyberFSR integration
  - Feature: Extended debugging capabilities (--dlss-debug=extra switch)

2.90.400
  - Feature: DLSS Enabler enables Hardware Accelerated GPU Scheduling (HAGS) by default (even on unsupported hardware). You can modify this behaviour by running your game with –dlss-hags=on/off/sys argument (where “sys” value tells the DLSS Enabler to honour the system wide HAGS setting).
  - Feature: --dlss-skip-validation no longer raises a warning if Hardware Accelerated GPU Scheduling is switched off/unsupported by the system, as long as –dlss-hags argument is not equal “sys” or “off”.
  - Feature: Due to NVIDIA license restrictions, after installing the optional AMD/Intel/GTX 8xx/9xx support module, installer will warn the user that additional, manual step is necessary (_nvngx.dll file needs to be provided by the end user on his/her own, by extracting it from NVIDIA drivers package and saving into the game directory).
  - Bugfix: Installer no longer shows the diagnostics window after the installation finishes (as due to the race condition, it often reported incorrect data). You can run the diagnostics process by running the game with –dlss-diagnostics argument.

2.90.300
  - Feature: Implemented functionality to enable Hardware Accelerated GPU Scheduling (HAGS) on GPUs that officially don't support that feature (AMD RDNA2, INTEL ARC, GTX 8xx/9xx cards). Use --dlss-hags=on switch together with --dlss-skip-validation to enable HAGS in game.
  - Feature: Added optional debug ini file to control the debug feature in Nukem9 DLSSG to FSR3 mod (file is deployed to game directory under the dlssg_to_fsr3.ini name)
  - Feature: More informative error message explaining the need to run dlss-enabler.exe with elevated rights if the game it needs to run requires them too
  - Feature: Updated error message telling what to do in cases when Hardware Accelerated GPU Scheduling is not supported by actual hardware
  - Bugfix: Validator looked for NVIDIA runtime files in the wrong directory during the installation process on AMD/INTEL cards.

2.90.200
  - Feature: Improved DLSSG support for AMD RDNA3 cards (do not install it if you're an owner of GTX/RTX card).

2.90.000
  - Feature: Updated DLSSG to FSR3 mod from version 0.81 to 0.90

2.81.200
  - Feature: Added experimental DLSSG support for AMD RDNA3 cards (do not install it if you don't need it!)
  - Feature: Implemented system diagnostic module, run the game with --dlss-diagnostics parameter to see the report (in DLL mode) or call dlss-enabler.exe with /g flag (in Executable mode).
  - Bugfix: Modified versioning pattern, now its a sum of DLLs enabler version (2.00.00) and bundled Nukem9 module (0.81) which results in version 2.81.x00

1.4.81
  - Bugfix/Feature: DLSS enabler DLL is now protected against possible unload from memory of the game
  - Bugfix: DLSS enabler DLL is now looking for the DLSSG files inside of the directory where the game executable is instead of current working directory (cwd). This is helpful for troubleshooting.
  - Feature: Considerable code refactoring
  - Feature: Updated DLLSG to FSR3 package to version 0.81

1.3.80
  - Feature: Installation package installs DLSS Enabler and Nukem9 DLSSG to FSR3 mod alltogether.
  - Feature: Nukem9 DLSSG to FSR3 mod installed by the installer no longer needs to have the NVIDIA Driver Signature Checks disabled
  - Feature: DLSS enabler DLL is able to detect if a custom version of the Nukem9 DLSSG to FSR3 mod is present in the game directory and loads it instead of the bundled one
  - Feature: DLSS enabler DLL comes equipped with an on-demand Debug Console that can be displayed after the game starts (just hit ctrl+` >twice< to show the console, and ctrl+` again to hide it or show it again)
  - Feature: DLSS enabler DLL is reading the DLSSG to FSR3 logs and presents them in Debug Console if its enabled.
  - Bugfix: No sudden RTD when starting the game with --dlss-off flag
  - Bugfix: Removed duplicate of version.dll file from the installation binary 
  - Bugfix/Feature: DLSS enabler DLL is now equipped with naive detection that protects itself from attaching to a crash reporting processes that are spawned by the game executable.

1.2.1
  - Bugfix: DLSS enabler DLL validation checked the wrong value type (BINARY instead of DWORD) responsible for NVIDIA signature checks
  - Feature: DLSS enabler DLL validation now suggests --dlss-skip-validation argument in case of validation failure

1.1.1
  - Bugfix: DLSS enabled DLL will now assume that HAGS is enabled by default if the appropriate registry key is missing, in such case --dlss-version message will report HAGS status as "enabled (inferred)" rather than just "enabled"

1.1.0
  - Feature: DLSS enabler DLL validates if HAGS is enabled, NVIDIA signature checking disabled and DLSS to FSR3 files present in game directory

1.0.4
  - Feature: DLSS enabler EXE starts the game without black window lingering in the backround till the game closes

1.0.3
  - Bugfix: DLSS enabler DLL used wrong architecture ID for Ada GPU

1.0.2
  - Feature: DLSS enabler DLL reports Ada architecture by default

1.0.1
  - Bugfix: DLSS enabler DLL typos fixed in various messages

1.0.0
  - Initial release



