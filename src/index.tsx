import { definePlugin } from "@decky/api";
import { MdOutlineAutoAwesomeMotion } from "react-icons/md";
import { useState, useEffect } from "react";
import { OptiScalerControls } from "./components";
// import { InstalledGamesSection } from "./components/InstalledGamesSection";
import { checkFGModPath } from "./api";
import { safeAsyncOperation } from "./utils";
import { TIMEOUTS } from "./utils/constants";

type FgmodInfo = {
  exists: boolean;
  version?: string | null;
  selected_fsr4_variant?: string | null;
  selected_fsr4_variant_label?: string | null;
  install_manifest_present?: boolean;
};

function MainContent() {
  const [pathExists, setPathExists] = useState<boolean | null>(null);
  const [fgmodInfo, setFgmodInfo] = useState<FgmodInfo | null>(null);

  useEffect(() => {
    const checkPath = async () => {
      const result = await safeAsyncOperation(
        async () => await checkFGModPath(),
        'MainContent -> checkPath'
      );
      if (result) {
        setFgmodInfo(result);
        setPathExists(result.exists);
      }
    };
    
    checkPath(); // Initial check
    const intervalId = setInterval(checkPath, TIMEOUTS.pathCheck); // Check every 3 seconds
    return () => clearInterval(intervalId); // Cleanup interval on component unmount
  }, []);

  return (
    <>
      <OptiScalerControls
        pathExists={pathExists}
        setPathExists={setPathExists}
        fgmodInfo={fgmodInfo}
      />
      {pathExists === true ? (
        <>
          {/* <InstalledGamesSection /> */}
        </>
      ) : null}
    </>
  );
}

export default definePlugin(() => ({
  name: "Decky Framegen",
  titleView: <div>Decky Framegen</div>,
  alwaysRender: true,
  content: <MainContent />,
  icon: <MdOutlineAutoAwesomeMotion />,
  onDismount() {
    console.log("Decky Framegen Plugin unmounted");
  },
}));
