# Decky-Framegen documentation landing page
#### Credits
- https://github.com/xXJSONDeruloXx/Decky-Framegen/graphs/contributors
- https://github.com/xXJSONDeruloXx/Decky-Framegen/blob/main/README.md

## Introduction
Decky-Framegen is a decky-loader plugint that merges various frame generation shims for use via Steam Big Picture (aka tenfoot) mode. 

## Installation
1. Install decky-loader fully and restart; [decky-loader GitHub](https://github.com/SteamDeckHomebrew/decky-loader), [YouTube guide by Deck Wizard - 10:35](https://www.youtube.com/watch?v=o_TkF-Eiq3M), [YouTube video by Grown Up Gaming - 10:20](https://www.youtube.com/watch?v=fGgc2CY6occ), [YouTube video by Steam Deck In Hand - 6:34](https://www.youtube.com/watch?v=vAuOUY8IyHE)
2. Open Steam Big Picture mode
3. Use Guide+A to open the right sidebar, navigate to the new deckly-loader icon
4. Use the "Store" icon in the top right of decky-loader and use the interface to find Decky-Framegen most likely using the search term "framegen"
5. Select Install and wait
- If the installer appears to hang or take abnormally long; wait for it to time out
- If the plugin doesn't appear to have installed; one may need to restart the decky-loader service. A system restart carries out the same function
8. Select the desired game to modify with the modification from the dropdown menu, then select Install or Uninstall as required
- If the game fails to launch, the first step should be to uninstall the Decky-Framegen shim before carrying out other fault finding steps (https://github.com/xXJSONDeruloXx/Decky-Framegen/issues/39#issuecomment-2644123721)
- Manually or automatically installing Decky-Framegen into a non-Steam game will require manual installation using the .sh script in the games directory (https://github.com/xXJSONDeruloXx/Decky-Framegen/issues/109#issuecomment-3014959984)
9. In your Home directory you will now have `~/fgmod/` with an `fgmod` binary within it if the installation was successful

### Installation beyond Steam
`~/fgmod/fgmod %command%` for all instances of running a game or other program with Decky-Framegen

## Limitations
- Decky-Framegen only adds a shim from existing DLSS/FSR/Intel fake frame support to existing DLSS/FSR/Inel fake frame support
- It does not add support for FG for games that do not support FG in the first place
- All plugins are the creation of their original creators, DFG only provides a shim to automate their installation
- Decky-Framegen only works on games that use the DX12 graphics API
### List of DX12 games
https://www.pcgamingwiki.com/wiki/List_of_Direct3D_12_games
