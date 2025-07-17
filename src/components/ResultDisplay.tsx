import { PanelSectionRow } from "@decky/ui";
import { FC } from "react";
import { STYLES } from "../utils/constants";
import { ApiResponse } from "../types/index";

export type OperationResult = ApiResponse;

interface ResultDisplayProps {
  result: OperationResult | null;
}

export const ResultDisplay: FC<ResultDisplayProps> = ({ result }) => {
  if (!result) return null;

  return (
    <PanelSectionRow>
      <div>
        <strong>Status:</strong>{" "}
        <span style={result.status === "success" ? STYLES.statusSuccess : STYLES.statusError}>
          {result.status === "success" ? "Success" : "Error"}
        </span>
        <br />
        {result.output ? (
          <>
            <strong>Output:</strong>
            <pre style={STYLES.preWrap}>{result.output}</pre>
          </>
        ) : null}
        {result.message ? (
          <>
            <strong>Error:</strong> {result.message}
          </>
        ) : null}
      </div>
    </PanelSectionRow>
  );
};
