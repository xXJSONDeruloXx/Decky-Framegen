import { useState, useEffect } from "react";
import {
  PanelSection,
  PanelSectionRow,
  ButtonItem,
  DropdownItem
} from "@decky/ui";
import { definePlugin, callable } from "@decky/api";
import { RiAiGenerate } from "react-icons/ri";

const runInstallFGMod = callable<
  [],
  { status: string; message?: string; output?: string }
>("run_install_fgmod");

const runUninstallFGMod = callable<
  [],
  { status: string; message?: string; output?: string }
>("run_uninstall_fgmod");

const checkFGModPath = callable<
  [],
  { exists: boolean }
>("check_fgmod_path");

const listInstalledGames = callable<
  [],
  { status: string; games: { appid: string; name: string }[] }
>("list_installed_games");

const logError = callable<[string], void>("log_error");

function FGModInstallerSection() {
  const [installing, setInstalling] = useState(false);
  const [uninstalling, setUninstalling] = useState(false);
  const [installResult, setInstallResult] = useState<{
    status: string;
    output?: string;
    message?: string;
  } | null>(null);
  const [uninstallResult, setUninstallResult] = useState<{
    status: string;
    output?: string;
    message?: string;
  } | null>(null);
  const [pathExists, setPathExists] = useState<boolean | null>(null);

  useEffect(() => {
    const checkPath = async () => {
      try {
        const result = await checkFGModPath();
        setPathExists(result.exists);
      } catch (e) {
        logError('useEffect -> checkPath' + String(e));
        console.error(e);
      }
    };
    checkPath(); // Initial check
    const intervalId = setInterval(checkPath, 3000); // Check every 3 seconds
    return () => clearInterval(intervalId); // Cleanup interval on component unmount
  }, []);

  useEffect(() => {
    if (installResult) {
      const timer = setTimeout(() => {
        setInstallResult(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
    return () => {}; // Ensure a cleanup function is always returned
  }, [installResult]);

  useEffect(() => {
    if (uninstallResult) {
      const timer = setTimeout(() => {
        setUninstallResult(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
    return () => {};
  }, [uninstallResult]);

  const handleInstallClick = async () => {
    try {
      setInstalling(true);
      const result = await runInstallFGMod();
      setInstalling(false);
      setInstallResult(result);
    } catch (e) {
      logError('handleInstallClick: ' + String(e));
      console.error(e)
    }
  };

  const handleUninstallClick = async () => {
    try {
      setUninstalling(true);
      const result = await runUninstallFGMod();
      setUninstalling(false);
      setUninstallResult(result);
    } catch (e) {
      logError('handleUninstallClick' + String(e));
      console.error(e)
    }
  };

  return (
    <PanelSection>
      {pathExists !== null ? (
        <PanelSectionRow>
          <div style={{ color: pathExists ? "green" : "red" }}>
            {pathExists ? "Mod Is Installed" : "Mod Not Installed"}
          </div>
        </PanelSectionRow>
      ) : null}
      {pathExists === false ? (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={handleInstallClick} disabled={installing}>
            {installing ? "Installing..." : "Install FG Mod"}
          </ButtonItem>
        </PanelSectionRow>
      ) : null}
      {pathExists === true ? (
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={handleUninstallClick} disabled={uninstalling}>
            {uninstalling ? "Uninstalling..." : "Uninstall FG Mod"}
          </ButtonItem>
        </PanelSectionRow>
      ) : null}
      {installResult ? (
        <PanelSectionRow>
          <div>
            <strong>Status:</strong>{" "}
            {installResult.status === "success" ? "Success" : "Error"}
            <br />
            {installResult.output ? (
              <>
                <strong>Output:</strong>
                <pre style={{ whiteSpace: "pre-wrap" }}>{installResult.output}</pre>
              </>
            ) : null}
            {installResult.message ? (
              <>
                <strong>Error:</strong> {installResult.message}
              </>
            ) : null}
          </div>
        </PanelSectionRow>
      ) : null}
      {uninstallResult ? (
        <PanelSectionRow>
          <div>
            <strong>Status:</strong>{" "}
            {uninstallResult.status === "success" ? "Success" : "Error"}
            <br />
            {uninstallResult.output ? (
              <>
                <strong>Output:</strong>
                <pre style={{ whiteSpace: "pre-wrap" }}>{uninstallResult.output}</pre>
              </>
            ) : null}
            {uninstallResult.message ? (
              <>
                <strong>Error:</strong> {uninstallResult.message}
              </>
            ) : null}
          </div>
        </PanelSectionRow>
      ) : null}
      <PanelSectionRow>
        <div>
          Once installed, patch a games below to replace DLSS upscale and frame gen options with FSR 3 equivalents. * NON STEAM GAMES, GAMES WITH LAUNCHERS, AND DX11 OR BELOW NOT SUPPORTED.
        </div>
      </PanelSectionRow>
    </PanelSection>
  );
}

function InstalledGamesSection() {
  const [games, setGames] = useState<{ appid: number; name: string }[]>([]);
  const [selectedGame, setSelectedGame] = useState<{ appid: number; name: string } | null>(null);
  const [result, setResult] = useState<string>('');

  useEffect(() => {
    const fetchGames = async () => {
      try {
        const response = await listInstalledGames();
        if (response.status === "success") {
          const sortedGames = [...response.games]
            .map(game => ({
              ...game,
              appid: parseInt(game.appid, 10),
            }))
            .sort((a, b) => a.name.toLowerCase().localeCompare(b.name.toLowerCase()));
          setGames(sortedGames);
        } else {
          logError('fetchGames: ' + JSON.stringify(response));
          console.error('fetchGames: ' + JSON.stringify(response));
        }
      } catch (error) {
        logError("Error fetching games:" + String(error));
        console.error("Error fetching games:", String(error));
      }
    };
    fetchGames();
  }, []);

  const handlePatchClick = async () => {
    if (!selectedGame) return;

    try {
      await SteamClient.Apps.SetAppLaunchOptions(selectedGame.appid, '~/fgmod/fgmod %COMMAND%');
      setResult(`Launch options set successfully for ${selectedGame.name}. You can now select DLSS in the game's menu to use FSR Upscaling and FrameGen equivalents.`);
    } catch (error) {
      logError('handlePatchClick: ' + String(error));
      setResult(error instanceof Error ? `Error setting launch options: ${error.message}` : 'Error setting launch options');
    }
  };

  const handleUnpatchClick = async () => {
    if (!selectedGame) return;

    try {
      await SteamClient.Apps.SetAppLaunchOptions(selectedGame.appid, '~/fgmod/fgmod-uninstaller.sh %COMMAND%');
      setResult(`DLSS mods will uninstall on next launch of ${selectedGame.name}. The game is now unpatched.`);
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
      
      {selectedGame ? (
        <>
          <PanelSectionRow>
            <div style={{ fontWeight: 'bold', fontSize: '1.1em' }}>
              {selectedGame.name}
            </div>
          </PanelSectionRow>
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

      {result ? (
        <PanelSectionRow>
          <div style={{ 
            padding: '12px',
            marginTop: '16px',
            backgroundColor: 'var(--decky-selected-ui-bg)',
            borderRadius: '4px'
          }}>
            {result}
          </div>
        </PanelSectionRow>
      ) : null}
    </PanelSection>
  );
}

export default definePlugin(() => ({
  name: "Framegen Plugin",
  titleView: <div>Decky Framegen</div>,
  alwaysRender: true,
  content: (
    <>
      <FGModInstallerSection />
      <InstalledGamesSection />
    </>
  ),
  icon: <RiAiGenerate />,
  onDismount() {
    console.log("Framegen Plugin unmounted");
  },
}));
