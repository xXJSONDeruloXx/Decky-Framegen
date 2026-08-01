"""Steam library discovery and conservative executable selection."""

import re
import subprocess
from pathlib import Path
from typing import Callable


Logger = Callable[[str], None]

BAD_EXE_SUBSTRINGS = [
    "crashreport",
    "crashreportclient",
    "eac",
    "easyanticheat",
    "beclient",
    "eosbootstrap",
    "benchmark",
    "uninstall",
    "setup",
    "launcher",
    "updater",
    "bootstrap",
    "_redist",
    "prereq",
]


class SteamLibrary:
    def __init__(self, home: Path, logger: Logger):
        self.home = home
        self.logger = logger

    def steam_common_path(self) -> Path:
        return self.home / ".local" / "share" / "Steam" / "steamapps" / "common"

    def _steam_root_candidates(self) -> list[Path]:
        candidates = [
            self.home / ".local" / "share" / "Steam",
            self.home / ".steam" / "steam",
            self.home / ".steam" / "root",
            self.home / ".var" / "app" / "com.valvesoftware.Steam" / "home" / ".local" / "share" / "Steam",
            self.home / ".var" / "app" / "com.valvesoftware.Steam" / "home" / ".steam" / "steam",
        ]
        unique: list[Path] = []
        seen: set[str] = set()
        for candidate in candidates:
            key = str(candidate)
            if key not in seen:
                unique.append(candidate)
                seen.add(key)
        return unique

    def _steam_library_paths(self) -> list[Path]:
        library_paths: list[Path] = []
        seen: set[str] = set()
        for steam_root in self._steam_root_candidates():
            if steam_root.exists() and str(steam_root) not in seen:
                library_paths.append(steam_root)
                seen.add(str(steam_root))
            library_file = steam_root / "steamapps" / "libraryfolders.vdf"
            if not library_file.exists():
                continue
            try:
                for line in library_file.read_text(encoding="utf-8", errors="replace").splitlines():
                    if '"path"' not in line:
                        continue
                    path = line.split('"path"', 1)[1].strip().strip('"').replace("\\\\", "/")
                    candidate = Path(path)
                    if str(candidate) not in seen:
                        library_paths.append(candidate)
                        seen.add(str(candidate))
            except OSError as exc:
                self.logger(f"[Framegen] failed to parse libraryfolders: {library_file}: {exc}")
        return library_paths

    def find_installed_games(self, appid: str | None = None) -> list[dict]:
        games: list[dict] = []
        for library_path in self._steam_library_paths():
            steamapps_path = library_path / "steamapps"
            if not steamapps_path.exists():
                continue
            for appmanifest in steamapps_path.glob("appmanifest_*.acf"):
                game_info: dict = {
                    "appid": "",
                    "name": "",
                    "library_path": str(library_path),
                    "install_path": "",
                }
                install_dir = ""
                try:
                    for line in appmanifest.read_text(encoding="utf-8", errors="replace").splitlines():
                        if '"appid"' in line:
                            game_info["appid"] = line.split('"appid"', 1)[1].strip().strip('"')
                        elif '"name"' in line:
                            game_info["name"] = line.split('"name"', 1)[1].strip().strip('"')
                        elif '"installdir"' in line:
                            install_dir = line.split('"installdir"', 1)[1].strip().strip('"')
                except OSError as exc:
                    self.logger(f"[Framegen] skipping manifest {appmanifest}: {exc}")
                    continue
                if not game_info["appid"] or not game_info["name"]:
                    continue
                if "Proton" in game_info["name"] or "Steam Linux Runtime" in game_info["name"]:
                    continue
                game_info["install_path"] = str(steamapps_path / "common" / install_dir) if install_dir else str(Path())
                if appid is None or str(game_info["appid"]) == str(appid):
                    games.append(game_info)
        deduped = {str(game["appid"]): game for game in games}
        return sorted(deduped.values(), key=lambda game: game["name"].lower())

    def game_record(self, appid: str) -> dict | None:
        matches = self.find_installed_games(appid)
        return matches[0] if matches else None

    @staticmethod
    def normalized_path_string(value: str) -> str:
        normalized = value.lower().replace("\\", "/")
        normalized = normalized.replace("z:/", "/")
        return normalized.replace("//", "/")

    def candidate_executables(self, install_root: Path) -> list[Path]:
        if not install_root.exists():
            return []
        try:
            return [exe for exe in install_root.rglob("*.exe") if exe.is_file()]
        except OSError as exc:
            self.logger(f"[Framegen] exe scan failed for {install_root}: {exc}")
            return []

    def _exe_score(self, exe: Path, install_root: Path, game_name: str) -> int:
        normalized = self.normalized_path_string(str(exe))
        name = exe.name.lower()
        score = 0
        if normalized.endswith("-win64-shipping.exe"):
            score += 300
        if "shipping.exe" in name:
            score += 220
        if "/binaries/win64/" in normalized:
            score += 200
        if "/win64/" in normalized:
            score += 80
        if exe.parent == install_root:
            score += 20
        sanitized_game = re.sub(r"[^a-z0-9]", "", game_name.lower())
        sanitized_name = re.sub(r"[^a-z0-9]", "", exe.stem.lower())
        sanitized_root = re.sub(r"[^a-z0-9]", "", install_root.name.lower())
        if sanitized_game and sanitized_game in sanitized_name:
            score += 120
        if sanitized_root and sanitized_root in sanitized_name:
            score += 90
        for bad in BAD_EXE_SUBSTRINGS:
            if bad in normalized:
                score -= 200
        return score - len(exe.parts)

    def best_running_executable(self, candidates: list[Path]) -> Path | None:
        if not candidates:
            return None
        try:
            result = subprocess.run(["ps", "-eo", "args="], capture_output=True, text=True, check=False)
            process_lines = result.stdout.splitlines()
        except OSError as exc:
            self.logger(f"[Framegen] running exe scan failed: {exc}")
            return None
        normalized_candidates = [(exe, self.normalized_path_string(str(exe))) for exe in candidates]
        matches: list[tuple[int, Path]] = []
        for line in process_lines:
            normalized_line = self.normalized_path_string(line)
            for exe, normalized_exe in normalized_candidates:
                if normalized_exe in normalized_line:
                    matches.append((len(normalized_exe), exe))
        return max(matches, key=lambda item: item[0])[1] if matches else None

    def guess_patch_target(self, game_info: dict) -> tuple[Path, Path | None]:
        install_root = Path(game_info["install_path"])
        candidates = self.candidate_executables(install_root)
        if not candidates:
            return install_root, None
        running_exe = self.best_running_executable(candidates)
        if running_exe:
            return running_exe.parent, running_exe
        best = max(candidates, key=lambda exe: self._exe_score(exe, install_root, game_info["name"]))
        return best.parent, best

    def is_game_running(self, game_info: dict) -> bool:
        return self.best_running_executable(self.candidate_executables(Path(game_info["install_path"]))) is not None
