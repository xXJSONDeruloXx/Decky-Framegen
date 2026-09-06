import { Navigation, PanelSectionRow, ButtonItem } from "@decky/ui";
import { FaBook } from "react-icons/fa";

interface OptiScalerWikiProps {
  pathExists: boolean | null;
}

const WIKI_URL = "https://github.com/optiscaler/OptiScaler/wiki";

export function OptiScalerWiki({ pathExists }: OptiScalerWikiProps) {
  if (pathExists !== true) return null;

  const handleWikiClick = () => {
    // Decky's supported way to open a URL from Gaming Mode (Steam's overlay browser);
    // fall back to window.open so this can never do less than before.
    if (typeof Navigation?.NavigateToExternalWeb === "function") {
      Navigation.NavigateToExternalWeb(WIKI_URL);
    } else {
      window.open(WIKI_URL, "_blank");
    }
  };

  return (
    <PanelSectionRow>
      <ButtonItem
        layout="below"
        onClick={handleWikiClick}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <FaBook />
          <div>OptiScaler Wiki</div>
        </div>
      </ButtonItem>
    </PanelSectionRow>
  );
}
