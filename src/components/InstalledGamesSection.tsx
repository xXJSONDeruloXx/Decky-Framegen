import { useState, useEffect } from "react";
import { PanelSection, PanelSectionRow, ButtonItem, DropdownItem, ConfirmModal, showModal } from "@decky/ui";
import { listInstalledGames, logError } from "../api";
import { safeAsyncOperation } from "../utils";
import { STYLES } from "../utils/constants";
import { GameInfo } from "../types/index";

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
        void logError('fetchGames: ' + JSON.stringify(response));
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
        strTitle={`Enable Frame Generation for ${selectedGame.name}?`}
        strDescription={
          "⚠️ Important: This plugin does not automatically unpatch games when uninstalled. If you uninstall this plugin or experience game issues, use the 'Disable Frame Generation' option or verify game file integrity through Steam."
        }
        strOKButtonText="Enable Frame Generation"
        strCancelButtonText="Cancel"
        onOK={async () => {
          try {
            await SteamClient.Apps.SetAppLaunchOptions(selectedGame.appid, '~/fgmod/fgmod %COMMAND%');
            setResult(`✓ Frame generation enabled for ${selectedGame.name}. Launch the game, enable DLSS in graphics settings, then press Insert to access OptiScaler options.`);
          } catch (error) {
            void logError('handlePatchClick: ' + String(error));
            setResult(error instanceof Error ? `Error: ${error.message}` : 'Error enabling frame generation');
          }
        }}
      />
    );
  };

  const handleUnpatchClick = async () => {
    if (!selectedGame) return;

    try {
      await SteamClient.Apps.SetAppLaunchOptions(selectedGame.appid, '~/fgmod/fgmod-uninstaller.sh %COMMAND%');
      setResult(`✓ Frame generation will be disabled on next launch of ${selectedGame.name}.`);
    } catch (error) {
      void logError('handleUnpatchClick: ' + String(error));
      setResult(error instanceof Error ? `Error: ${error.message}` : 'Error disabling frame generation');
    }
  };

  return (
    <PanelSection title="Select a Game to Patch:">
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
          strDefaultLabel="Choose a game"
          menuLabel="Installed Games"
        />
      </PanelSectionRow>

      {result ? (
        <PanelSectionRow>
          <div style={{
            ...STYLES.preWrap,
            ...(result.includes('Error') ? STYLES.statusNotInstalled : STYLES.statusInstalled)
          }}>
            {result.includes('Error') ? '❌' : '✅'} {result}
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
              Enable Frame Generation
            </ButtonItem>
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={handleUnpatchClick}
            >
              Disable Frame Generation
            </ButtonItem>
          </PanelSectionRow>
        </>
      ) : null}
    </PanelSection>
  );
}
