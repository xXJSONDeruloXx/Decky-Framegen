import { PanelSectionRow } from "@decky/ui";
import optiScalerImage from "../../assets/header-banner.png";

interface OptiScalerHeaderProps {
  pathExists: boolean | null;
}

export function OptiScalerHeader({ pathExists }: OptiScalerHeaderProps) {
  if (pathExists !== true) return null;

  return (
    <PanelSectionRow>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'center', 
        marginBottom: '16px' 
      }}>
        <img 
          src={optiScalerImage} 
          alt="OptiScaler" 
          style={{ 
            maxWidth: '100%', 
            height: 'auto',
            borderRadius: '8px'
          }} 
        />
      </div>
    </PanelSectionRow>
  );
}
