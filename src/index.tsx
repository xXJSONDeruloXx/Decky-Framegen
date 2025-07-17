import { definePlugin } from "@decky/api";
import { RiAiGenerate } from "react-icons/ri";
import { FGModInstallerSection } from "./components/FGModInstallerSection";
import { InstalledGamesSection } from "./components/InstalledGamesSection";

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
