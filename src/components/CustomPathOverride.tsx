import { useCallback, useEffect, useMemo, useState } from "react";
import { ButtonItem, Field, PanelSectionRow, ToggleField } from "@decky/ui";
import { FileSelectionType, openFilePicker } from "@decky/api";
import { getPathDefaults } from "../api";
import type { CustomOverrideConfig } from "../types/index";

interface CustomPathOverrideProps {
  onOverrideChange: (override: CustomOverrideConfig | null) => void;
}

const DEFAULT_START_PATH = "/home";
const DEFAULT_STEAM_LIBRARY_PATH = "/home/deck/.local/share/Steam/steamapps/common";

interface PathDefaults {
  home: string;
  steamCommon: string;
}

const INITIAL_PATH_DEFAULTS: PathDefaults = {
  home: DEFAULT_START_PATH,
  steamCommon: DEFAULT_STEAM_LIBRARY_PATH,
};

const normalizePath = (path: string) => path.replace(/\\/g, "/");

const stripTrailingSlash = (value: string) =>
  value.endsWith("/") ? value.slice(0, -1) : value;

const escapeForDoubleQuotes = (value: string) =>
  value.replace(/[`"\\$]/g, (match) => `\\${match}`);

const escapeForPattern = (value: string) =>
  value
    .replace(/\\/g, "\\\\")
    .replace(/\//g, "\\/")
    .replace(/\[/g, "\\[")
    .replace(/\]/g, "\\]")
    .replace(/\*/g, "\\*")
    .replace(/\?/g, "\\?");

const escapeForReplacement = (value: string) =>
  value
    .replace(/\\/g, "\\\\")
    .replace(/\//g, "\\/")
    .replace(/\$/g, "\\$");

const quoteForShell = (value: string) => `'${value.replace(/'/g, "'\\''")}'`;

const dirname = (path: string) => {
  const normalized = normalizePath(path);
  const parts = normalized.split("/");
  parts.pop();
  const dir = parts.join("/");
  return dir.length > 0 ? dir : "/";
};

const longestCommonPrefix = (left: string[], right: string[]) => {
  const length = Math.min(left.length, right.length);
  let idx = 0;
  while (idx < length && left[idx] === right[idx]) {
    idx++;
  }
  return idx;
};

interface ComputedOverride {
  config: CustomOverrideConfig | null;
  error: string | null;
}

const buildOverride = (
  rawDefault: string | null,
  rawOverride: string | null
): ComputedOverride => {
  if (!rawDefault || !rawOverride) {
    return { config: null, error: null };
  }

  const defaultPath = normalizePath(rawDefault.trim());
  const overridePath = normalizePath(rawOverride.trim());

  if (defaultPath === overridePath) {
    return {
      config: null,
      error: "Paths are identical. Choose a different target executable.",
    };
  }

  const defaultParts = defaultPath.split("/").filter(Boolean);
  const overrideParts = overridePath.split("/").filter(Boolean);

  if (!defaultParts.length || !overrideParts.length) {
    return {
      config: null,
      error: "Unable to parse selected paths. Pick them again.",
    };
  }

  const prefixLength = longestCommonPrefix(defaultParts, overrideParts);

  if (prefixLength < 2) {
    return {
      config: null,
      error: "Selections do not share a common game folder.",
    };
  }

  const searchSuffixParts = defaultParts.slice(prefixLength);
  const replaceSuffixParts = overrideParts.slice(prefixLength);

  if (!searchSuffixParts.length || !replaceSuffixParts.length) {
    return {
      config: null,
      error: "Could not determine differing portion of the paths.",
    };
  }

  const searchSuffix = searchSuffixParts.join("/");
  const replaceSuffix = replaceSuffixParts.join("/");
  const pattern = defaultParts[prefixLength - 1] ?? defaultParts[defaultParts.length - 1];

  if (!pattern) {
    return {
      config: null,
      error: "Unable to infer game identifier from path.",
    };
  }

  const escapedPattern = escapeForDoubleQuotes(pattern);
  const escapedSearch = escapeForPattern(searchSuffix);
  const escapedReplace = escapeForReplacement(replaceSuffix);

  const expression = `[[ "$arg" == *"${escapedPattern}"* ]] && arg=\${arg//${escapedSearch}/${escapedReplace}}`;
  const snippet = `[[ "$arg" == *"${pattern}"* ]] && arg=\${arg//${searchSuffix}/${replaceSuffix}}`;
  const envAssignment = `FGMOD_OVERRIDE_EXPRESSION=${quoteForShell(expression)}`;

  const config: CustomOverrideConfig = {
    defaultPath,
    overridePath,
    pattern,
    searchSuffix,
    replaceSuffix,
    expression,
    snippet,
    envAssignment,
  };

  return { config, error: null };
};

export const CustomPathOverride = ({ onOverrideChange }: CustomPathOverrideProps) => {
  const [launcherPath, setLauncherPath] = useState<string | null>(null);
  const [overridePath, setOverridePath] = useState<string | null>(null);
  const [isEnabled, setEnabled] = useState(false);
  const [pathDefaults, setPathDefaults] = useState<PathDefaults>(INITIAL_PATH_DEFAULTS);

  useEffect(() => {
    let cancelled = false;

    const fetchDefaults = async () => {
      try {
        const result = await getPathDefaults();
        if (!result) {
          return;
        }

        const home = result.home ? normalizePath(result.home) : INITIAL_PATH_DEFAULTS.home;
        const steamCommonSource = result.steam_common
          ? normalizePath(result.steam_common)
          : normalizePath(`${stripTrailingSlash(home)}/.local/share/Steam/steamapps/common`);

        if (!cancelled) {
          setPathDefaults({
            home,
            steamCommon: steamCommonSource || INITIAL_PATH_DEFAULTS.steamCommon,
          });
        }
      } catch (err) {
        console.error("CustomPathOverride -> getPathDefaults", err);
      }
    };

    fetchDefaults();

    return () => {
      cancelled = true;
    };
  }, []);

  const { config, error } = useMemo(
    () => buildOverride(launcherPath, overridePath),
    [launcherPath, overridePath]
  );

  useEffect(() => {
    if (isEnabled && config) {
      onOverrideChange(config);
    } else {
      onOverrideChange(null);
    }
  }, [config, isEnabled, onOverrideChange]);

  interface PickerArgs {
    existing: string | null;
    setter: (value: string) => void;
    fallbackStart?: string | null;
  }

  const openPicker = useCallback(
    async ({ existing, setter, fallbackStart }: PickerArgs) => {
      const candidates = new Set<string>();

      if (existing) {
        candidates.add(normalizePath(existing));
      } else {
        if (fallbackStart) {
          candidates.add(normalizePath(fallbackStart));
        }
        candidates.add(pathDefaults.steamCommon);
        candidates.add(pathDefaults.home);
      }

      let lastError: unknown = null;

      for (const candidate of candidates) {
        if (!candidate) {
          continue;
        }

        try {
          const result = await openFilePicker(
            FileSelectionType.FILE,
            candidate,
            true,
            true,
            undefined,
            undefined,
            true
          );

          if (result?.path) {
            setter(normalizePath(result.path));
            return;
          }
        } catch (err) {
          lastError = err;
        }
      }

      if (lastError) {
        console.error("CustomPathOverride -> openPicker", lastError);
      }
    },
    [pathDefaults]
  );

  const handleToggle = (value: boolean) => {
    setEnabled(value);
    if (!value) {
      setLauncherPath(null);
      setOverridePath(null);
      onOverrideChange(null);
    } else if (config) {
      onOverrideChange(config);
    }
  };

  return (
    <>
      <PanelSectionRow>
        <ToggleField
          label="Custom Launcher Override"
          description="Select launcher and target executables from the Deck's file browser."
          checked={isEnabled}
          onChange={handleToggle}
        />
      </PanelSectionRow>

      {isEnabled && (
        <>
          <PanelSectionRow>
            <ButtonItem
              layout="below"
              onClick={() =>
                openPicker({
                  existing: launcherPath,
                  setter: setLauncherPath,
                  fallbackStart: pathDefaults.steamCommon,
                })
              }
              description={launcherPath || "Pick the EXE Steam currently uses."}
            >
              Select Steam-provided EXE
            </ButtonItem>
          </PanelSectionRow>

          <PanelSectionRow>
            <ButtonItem
              layout="below"
              disabled={!launcherPath}
              onClick={() =>
                launcherPath &&
                openPicker({
                  existing: overridePath,
                  setter: setOverridePath,
                  fallbackStart: launcherPath ? dirname(launcherPath) : pathDefaults.steamCommon,
                })
              }
              description={
                launcherPath
                  ? overridePath || "Pick the executable that should run instead."
                  : "Select the Steam-provided executable first."
              }
            >
              Select Override EXE
            </ButtonItem>
          </PanelSectionRow>

          {(launcherPath || overridePath) && (
            <PanelSectionRow>
              <ButtonItem
                layout="below"
                onClick={() => {
                  setLauncherPath(null);
                  setOverridePath(null);
                }}
              >
                Clear selections
              </ButtonItem>
            </PanelSectionRow>
          )}

          {error && (
            <PanelSectionRow>
              <Field
                label="Override status"
                description={error}
              >
                ⚠️
              </Field>
            </PanelSectionRow>
          )}

          {!error && config && (
            <>
              <PanelSectionRow>
                <Field
                  label="Detected game"
                  description="Based on the shared folder between both selections."
                >
                  {config.pattern}
                </Field>
              </PanelSectionRow>

              <PanelSectionRow>
                <Field
                  label="Code snippet"
                  description="This is added to fgmod before resolving the install path."
                  bottomSeparator="none"
                >
                  <div
                    style={{
                      backgroundColor: "rgba(255,255,255,0.05)",
                      borderRadius: "6px",
                      padding: "12px",
                      fontFamily: "monospace",
                      whiteSpace: "pre-wrap",
                      wordBreak: "break-word",
                    }}
                  >
                    {config.snippet}
                  </div>
                </Field>
              </PanelSectionRow>

              <PanelSectionRow>
                <Field
                  label="Environment preview"
                  description="Automatically appended to the Patch command."
                >
                  {config.envAssignment}
                </Field>
              </PanelSectionRow>
            </>
          )}
        </>
      )}
    </>
  );
};