import { PanelSectionRow } from "@decky/ui";
import { MESSAGES, STYLES } from "../utils/constants";

interface InstructionCardProps {
  pathExists: boolean | null;
}

export function InstructionCard({ pathExists }: InstructionCardProps) {
  if (pathExists !== true) return null;

  return (
    <PanelSectionRow>
      <div style={STYLES.instructionCard}>
        <div style={{ fontWeight: 'bold', marginBottom: '8px', color: 'var(--decky-accent-text)' }}>
          {MESSAGES.instructionTitle}
        </div>
        <div style={{ whiteSpace: 'pre-line' }}>
          {MESSAGES.instructionText}
        </div>
      </div>
    </PanelSectionRow>
  );
}
