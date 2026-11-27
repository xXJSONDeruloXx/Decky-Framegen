import { PanelSectionRow } from "@decky/ui";
import { FC } from "react";
import { STYLES } from "../utils/constants";
import { ApiResponse } from "../types/index";
import { L } from "../utils/i18n";

export type OperationResult = ApiResponse;

interface ResultDisplayProps {
  result: OperationResult | null;
}

export const ResultDisplay: FC<ResultDisplayProps> = ({ result }) => {
  if (!result) return null;

  const isSuccess = result.status === "success";
  
  return (
    <PanelSectionRow>
      <div style={isSuccess ? STYLES.statusInstalled : STYLES.statusNotInstalled}>
        {isSuccess ? (
          <>
            {result.output?.includes("uninstall") || result.output?.includes("remov") 
              ? L("OptiScaler mod removed successfully", "OptiScaler 模組已成功移除")
              : L("OptiScaler mod installed successfully", "OptiScaler 模組已成功安裝")}
          </>
        ) : (
          <>
            <strong>{L("Error:", "錯誤：")}</strong> {result.message || L("Operation failed", "操作失敗")}
          </>
        )}
        {result.output && !isSuccess && (
          <details style={{ marginTop: '8px' }}>
            <summary style={{ cursor: 'pointer', fontSize: '12px' }}>{L("View Details", "檢視詳細資訊")}</summary>
            <pre style={{ ...STYLES.preWrap, fontSize: '11px', marginTop: '4px' }}>
              {result.output}
            </pre>
          </details>
        )}
      </div>
    </PanelSectionRow>
  );
};
