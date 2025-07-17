import { PanelSection, PanelSectionRow, ButtonItem } from "@decky/ui";
import { FaExternalLinkAlt } from "react-icons/fa";

export function DocumentationButton() {
  const handleDocClick = () => {
    window.open("https://github.com/xXJSONDeruloXx/Decky-Framegen", "_blank");
  };

  return (
    <PanelSection>
      <PanelSectionRow>
        <ButtonItem
          layout="below"
          onClick={handleDocClick}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <FaExternalLinkAlt />
            <div>Wiki and Clipboard</div>
          </div>
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
