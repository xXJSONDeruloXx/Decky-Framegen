import { PanelSection, PanelSectionRow, ButtonItem } from "@decky/ui";
import { FaClipboard, FaBook } from "react-icons/fa";

export function DocumentationButton() {
  const handleDocClick = () => {
    window.open("https://github.com/xXJSONDeruloXx/Decky-Framegen/wiki", "_blank");
  };

  const handleOptiScalerClick = () => {
    window.open("https://github.com/optiscaler/OptiScaler/wiki", "_blank");
  };

  return (
    <PanelSection>
      {/* 
      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={handleDocClick}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <FaClipboard />
            <div>Copy Launch Command</div>
          </div>
        </ButtonItem>
      </PanelSectionRow>
      */}
      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={handleOptiScalerClick}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <FaBook />
            <div>OptiScaler Wiki</div>
          </div>
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
