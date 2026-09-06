import { definePlugin } from "@decky/api";
import { useQuickAccessVisible } from "@decky/ui";
import { MdOutlineAutoAwesomeMotion } from "react-icons/md";
import { useState, useEffect } from "react";
import { OptiScalerControls } from "./components";
import { checkFGModPath } from "./api";
import { safeAsyncOperation } from "./utils";
import { TIMEOUTS } from "./utils/constants";

type FgmodInfo = {
  exists: boolean;
  version?: string | null;
  selected_fsr4_variant?: string | null;
  selected_fsr4_variant_label?: string | null;
  install_manifest_present?: boolean;
  bundle_outdated?: boolean;
  outdated_variants?: string[];
};

function MainContent() {
  const [pathExists, setPathExists] = useState<boolean | null>(null);
  const [fgmodInfo, setFgmodInfo] = useState<FgmodInfo | null>(null);
  // `alwaysRender` keeps this component mounted while the Quick Access Menu is
  // closed; only poll the backend while the panel can actually be seen. The hook
  // reports "visible" if it cannot find the QAM window, i.e. it degrades to the
  // previous always-polling behaviour.
  const qamVisible = useQuickAccessVisible();

  useEffect(() => {
    if (!qamVisible) return;
    let inFlight = false;
    let cancelled = false;
    const checkPath = async () => {
      if (inFlight) return; // do not pile up calls while the backend is busy installing
      inFlight = true;
      try {
        const result = await safeAsyncOperation(
          async () => await checkFGModPath(),
          'MainContent -> checkPath'
        );
        if (result && !cancelled) {
          setFgmodInfo(result);
          setPathExists(result.exists);
        }
      } finally {
        inFlight = false;
      }
    };

    void checkPath(); // Initial check
    const intervalId = setInterval(checkPath, TIMEOUTS.pathCheck); // Check every 3 seconds while visible
    return () => {
      cancelled = true;
      clearInterval(intervalId);
    };
  }, [qamVisible]);

  return (
    <OptiScalerControls
      pathExists={pathExists}
      setPathExists={setPathExists}
      fgmodInfo={fgmodInfo}
    />
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
