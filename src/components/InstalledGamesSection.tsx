import { useEffect, useState } from "react";
import {
  ButtonItem,
  ConfirmModal,
  DropdownItem,
  PanelSection,
  PanelSectionRow,
  showModal,
} from "@decky/ui";
import { cleanupManagedGame, listInstalledGames, logError } from "../api";
import { safeAsyncOperation } from "../utils";
import { GameInfo } from "../types/index";
import { STYLES } from "../utils/constants";

const DEFAULT_LAUNCH_COMMAND = 'OPTISCALER_PROXY=winmm ~/fgmod/fgmod %COMMAND%';

interface InstalledGamesSectionProps {
  isAvailable: boolean;
}

export function InstalledGamesSection({ isAvailable }: InstalledGamesSectionProps) {
  const [games, setGames] = useState<GameInfo[]>([]);
  const [selectedGame, setSelectedGame] = useState<GameInfo | null>(null);
  const [result, setResult] = useState<string>("");
  const [loadingGames, setLoadingGames] = useState(false);
  const [enabling, setEnabling] = useState(false);
  const [disabling, setDisabling] = useState(false);

  useEffect(() => {
    if (!isAvailable) return;

    let cancelled = false;

    const fetchGames = async () => {
      setLoadingGames(true);
      const response = await safeAsyncOperation(async () => await listInstalledGames(), "InstalledGamesSection.fetchGames");

      if (cancelled || !response) {
        setLoadingGames(false);
        return;
      }

      if (response.status === "success") {
        const sortedGames = [...response.games]
          .map((game) => ({
            ...game,
            appid: parseInt(String(game.appid), 10),
          }))
          .sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
        setGames(sortedGames);
      } else {
        logError(`InstalledGamesSection.fetchGames: ${JSON.stringify(response)}`);
      }

      setLoadingGames(false);
    };

    fetchGames();

    return () => {
      cancelled = true;
    };
  }, [isAvailable]);

  const handleEnable = async () => {
    if (!selectedGame) return;

    showModal(
      <ConfirmModal
        strTitle={`Enable prefix-managed OptiScaler for ${selectedGame.name}?`}
        strDescription={
          "This only changes the Steam launch option for the selected game. OptiScaler itself is staged into compatdata/pfx/system32 at launch time and does not write into the game install directory."
        }
        strOKButtonText="Enable"
        strCancelButtonText="Cancel"
        onOK={async () => {
          setEnabling(true);
          try {
            await SteamClient.Apps.SetAppLaunchOptions(selectedGame.appid, DEFAULT_LAUNCH_COMMAND);
            setResult(`✓ Enabled prefix-managed OptiScaler for ${selectedGame.name}. Launch the game, enable DLSS if needed, then press Insert for the OptiScaler menu.`);
          } catch (error) {
            logError(`InstalledGamesSection.handleEnable: ${String(error)}`);
            setResult(error instanceof Error ? `Error: ${error.message}` : "Error enabling prefix-managed OptiScaler");
          } finally {
            setEnabling(false);
          }
        }}
      />
    );
  };

  const handleDisable = async () => {
    if (!selectedGame) return;

    setDisabling(true);
    try {
      const cleanupResult = await cleanupManagedGame(String(selectedGame.appid));
      if (cleanupResult?.status !== "success") {
        setResult(`Error: ${cleanupResult?.message || cleanupResult?.output || "Failed to clean managed compatdata prefix"}`);
        return;
      }

      await SteamClient.Apps.SetAppLaunchOptions(selectedGame.appid, "");
      setResult(`✓ Cleared launch options and cleaned the managed compatdata prefix for ${selectedGame.name}.`);
    } catch (error) {
      logError(`InstalledGamesSection.handleDisable: ${String(error)}`);
      setResult(error instanceof Error ? `Error: ${error.message}` : "Error disabling prefix-managed OptiScaler");
    } finally {
      setDisabling(false);
    }
  };

  if (!isAvailable) return null;

  return (
    <PanelSection title="Steam game integration">
      <PanelSectionRow>
        <DropdownItem
          rgOptions={games.map((game) => ({
            data: game.appid,
            label: game.name,
          }))}
          selectedOption={selectedGame?.appid}
          onChange={(option) => {
            const game = games.find((entry) => entry.appid === option.data);
            setSelectedGame(game || null);
            setResult("");
          }}
          strDefaultLabel={loadingGames ? "Loading installed games..." : "Choose a game"}
          menuLabel="Installed Steam games"
          disabled={loadingGames || games.length === 0}
        />
      </PanelSectionRow>

      <PanelSectionRow>
        <div style={STYLES.instructionCard}>
          Enable writes the launch option automatically. Disable clears launch options and removes staged files from the selected game's compatdata prefix.
        </div>
      </PanelSectionRow>

      {result ? (
        <PanelSectionRow>
          <div
            style={{
              ...STYLES.preWrap,
              ...(result.startsWith("Error") ? STYLES.statusNotInstalled : STYLES.statusInstalled),
            }}
          >
            {result.startsWith("Error") ? "❌" : "✅"} {result}
          </div>
        </PanelSectionRow>
      ) : null}

      {selectedGame ? (
        <>
          <PanelSectionRow>
            <ButtonItem layout="below" onClick={handleEnable} disabled={enabling || disabling}>
              {enabling ? "Enabling..." : "Enable for selected game"}
            </ButtonItem>
          </PanelSectionRow>
          <PanelSectionRow>
            <ButtonItem layout="below" onClick={handleDisable} disabled={enabling || disabling}>
              {disabling ? "Cleaning..." : "Disable and clean selected game"}
            </ButtonItem>
          </PanelSectionRow>
        </>
      ) : null}
    </PanelSection>
  );
}
