import { definePlugin } from "@decky/api";
import { RiAiGenerate } from "react-icons/ri";
import { FGModInstallerSection } from "./components/FGModInstallerSection";
import { InstalledGamesSection } from "./components/InstalledGamesSection";
import { DocumentationButton } from "./components/DocumentationButton";

export default definePlugin(() => ({
  name: "Framegen Plugin",
  titleView: <div>Decky Framegen</div>,
  alwaysRender: true,
  content: (
    <>
      <FGModInstallerSection />
      <InstalledGamesSection />
      <DocumentationButton />
    </>
  ),
  icon: <RiAiGenerate />,
  onDismount() {
    console.log("Framegen Plugin unmounted");
  },
}));
