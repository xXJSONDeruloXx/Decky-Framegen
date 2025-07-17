import { PanelSection, PanelSectionRow, ButtonItem } from "@decky/ui";
import { FaExternalLinkAlt } from "react-icons/fa";

export function DocumentationButton() {
  const handleDocClick = () => {
    window.open("https://github.com/xXJSONDeruloXx/Decky-Framegen/wiki", "_blank");
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
            <div>Copy Launch Command</div>
          </div>
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
}
