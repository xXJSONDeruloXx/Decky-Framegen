import { useState, useEffect } from "react";
import { PanelSection, PanelSectionRow, ButtonItem, DropdownItem, ConfirmModal, showModal } from "@decky/ui";
import { listInstalledGames, logError } from "../api";
import { safeAsyncOperation } from "../utils";
import { STYLES } from "../utils/constants";
import { GameInfo } from "../types";

export function InstalledGamesSection() {
  const [games, setGames] = useState<GameInfo[]>([]);
  const [selectedGame, setSelectedGame] = useState<GameInfo | null>(null);
  const [result, setResult] = useState<string>('');

  useEffect(() => {
    const fetchGames = async () => {
      const response = await safeAsyncOperation(
        async () => await listInstalledGames(),
        'fetchGames'
      );
      
      if (response?.status === "success") {
        const sortedGames = [...response.games]
          .map(game => ({
            ...game,
            appid: parseInt(game.appid, 10),
          }))
          .sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
        setGames(sortedGames);
      } else if (response) {
        logError('fetchGames: ' + JSON.stringify(response));
        console.error('fetchGames: ' + JSON.stringify(response));
      }
    };
    
    fetchGames();
  }, []);

  const handlePatchClick = async () => {
    if (!selectedGame) return;

    // Show confirmation modal
    showModal(
      <ConfirmModal 
        strTitle={`Patch ${selectedGame.name}?`}
        strDescription={
          "WARNING: Decky Framegen does not unpatch games when uninstalled. Be sure to unpatch the game or verify the integrity of your game files if you choose to uninstall the plugin or the game has issues."
        }
        strOKButtonText="Yeah man, I wanna do it"
        strCancelButtonText="Cancel"
        onOK={async () => {
          try {
            await SteamClient.Apps.SetAppLaunchOptions(selectedGame.appid, '~/fgmod/fgmod %COMMAND%');
            setResult(`Launch options set for ${selectedGame.name}. You can now select DLSS in the game's menu, and access OptiScaler with Insert key.`);
          } catch (error) {
            logError('handlePatchClick: ' + String(error));
            setResult(error instanceof Error ? `Error setting launch options: ${error.message}` : 'Error setting launch options');
          }
        }}
      />
    );
  };

  const handleUnpatchClick = async () => {
    if (!selectedGame) return;

    try {
      await SteamClient.Apps.SetAppLaunchOptions(selectedGame.appid, '~/fgmod/fgmod-uninstaller.sh %COMMAND%');
      setResult(`OptiScaler will uninstall on next launch of ${selectedGame.name}.`);
    } catch (error) {
      logError('handleUnpatchClick: ' + String(error));
      setResult(error instanceof Error ? `Error clearing launch options: ${error.message}` : 'Error clearing launch options');
    }
  };

  return (
    <PanelSection title="Select a game to patch:">
      <PanelSectionRow>
        <DropdownItem
          rgOptions={games.map(game => ({
            data: game.appid,
            label: game.name
          }))}
          selectedOption={selectedGame?.appid}
          onChange={(option) => {
            const game = games.find(g => g.appid === option.data);
            setSelectedGame(game || null);
            setResult('');
          }}
          strDefaultLabel="Select a game..."
          menuLabel="Installed Games"
        />
      </PanelSectionRow>

      {result ? (
        <PanelSectionRow>
          <div style={STYLES.resultBox}>
            {result}
          </div>
        </PanelSectionRow>
      ) : null}
      
      {selectedGame ? (
        <>
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={handlePatchClick}
            >
              Patch
            </ButtonItem>
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={handleUnpatchClick}
            >
              Unpatch
            </ButtonItem>
          </PanelSectionRow>
        </>
      ) : null}
    </PanelSection>
  );
}
