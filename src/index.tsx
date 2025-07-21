import { definePlugin } from "@decky/api";
import { RiAiGenerate } from "react-icons/ri";
import { useState, useEffect } from "react";
import { FGModInstallerSection } from "./components/FGModInstallerSection";
import { InstalledGamesSection } from "./components/InstalledGamesSection";
import { DocumentationButton } from "./components/DocumentationButton";
import { checkFGModPath } from "./api";
import { safeAsyncOperation } from "./utils";
import { TIMEOUTS } from "./utils/constants";

function MainContent() {
  const [pathExists, setPathExists] = useState<boolean | null>(null);

  useEffect(() => {
    const checkPath = async () => {
      const result = await safeAsyncOperation(
        async () => await checkFGModPath(),
        'MainContent -> checkPath'
      );
      if (result) setPathExists(result.exists);
    };
    
    checkPath(); // Initial check
    const intervalId = setInterval(checkPath, TIMEOUTS.pathCheck); // Check every 3 seconds
    return () => clearInterval(intervalId); // Cleanup interval on component unmount
  }, []);

  return (
    <>
      <FGModInstallerSection pathExists={pathExists} setPathExists={setPathExists} />
      {pathExists === true ? (
        <>
          {/* <InstalledGamesSection /> */}
          <DocumentationButton />
        </>
      ) : null}
    </>
  );
}

export default definePlugin(() => ({
  name: "Framegen Plugin",
  titleView: <div>Decky Framegen</div>,
  alwaysRender: true,
  content: <MainContent />,
  icon: <RiAiGenerate />,
  onDismount() {
    console.log("Framegen Plugin unmounted");
  },
}));
