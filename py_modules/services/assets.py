"""Static asset metadata and patch file inventories."""

OPTISCALER_ARCHIVE_ASSET = {
    "name": "Optiscaler_0.9.4-final.20260718._MM.7z",
    "sha256": "575cb4df866116093df75af607e37fd70e10f5163e0f23fd5c804142e80ef0ad",
    "version": "0.9.4-final.20260718",
}

FSR4_INT8_ASSET = {
    "name": "amd_fidelityfx_upscaler_dx12.dll",
    "sha256": "c7720bc16bede334f59a1a32cd22edbcbbb159685ed5240e61350a5fb0bc8a94",
    "version": "4.0.2c",
}

FSR4_OFFICIAL_411_ASSET = {
    "name": "amdxcffx64.dll",
    "sha256": "a2b136b6affd35a49b141a936be935f7d5ddc8d8f9b8c9afbe62ff9ddb2538a0",
    "version": "4.1.1-official",
}

FSR4_VALVE_411_ASSET = {
    "name": "amdxcffx64_valve_2.3.0.2913.dll",
    "sha256": "4e7dc37aebea3a90e3d3cc43e24cb2b54176b2535315f20dbe63b3b7cfc56b1e",
    "version": "4.1.1-valve-2.3.0.2913",
}

AMDXC64_RDNA2_ASSET = {
    "name": "amdxc64.dll",
    "sha256": "a0a0af61d475e30a70966b3459f3793df772faf8f26ae3261d10554ff592cbd5",
    "version": "8.18.10.0474",
}

OPTISCALER_PRE10_ASSET = {
    "name": "OptiScaler_0.10.0-pre1.20260622_135940.dll",
    "sha256": "b374b19081cc066365d0c6da4808d768e16469b0cbdfc478b6e95999947d5364",
    "version": "0.10.0-pre1.20260622_135940",
}

OPTIPATCHER_ASSET = {
    "name": "OptiPatcher_rolling.asi",
    "sha256": "88b9e1be3559737cd205fdf5f2c8550cf1923fb1def4c603e5bf03c3e84131b1",
    "version": "rolling",
}

FSR4_UPSCALER_FILENAME = "amd_fidelityfx_upscaler_dx12.dll"
FSR4_DRIVER_OVERRIDE_FILENAME = "amdxcffx64.dll"
INSTALL_MANIFEST_FILENAME = "install-manifest.json"
VERSION_FILENAME = "version.txt"
DEFAULT_FSR4_VARIANT = "rdna23-int8"
DEFAULT_FRAMEGEN_BACKEND = "auto"
FRAMEGEN_BACKENDS = {
    "auto": "OptiScaler automatic selection",
    "nukems": "Nukem's DLSSG → FSR3",
}

FSR4_VARIANTS = {
    "rdna23-int8": {
        "label": "4.0.2c / RDNA2-3 compatibility",
        "dir_name": "fsr4-rdna2-3",
        "sha256": "c7720bc16bede334f59a1a32cd22edbcbbb159685ed5240e61350a5fb0bc8a94",
        "source_asset_name": FSR4_INT8_ASSET["name"],
        "source_version": FSR4_INT8_ASSET["version"],
        "uses_archive_native": False,
        "extra_files": [],
    },
    "rdna4-native": {
        "label": "4.1.1 SDK / RDNA3 dGPU + RDNA4",
        "dir_name": "fsr4-rdna4",
        "sha256": "d0dcccc74a43c44ba435b7a369b456e0970d8a4464e4bd683119b374f2c9fb46",
        "source_asset_name": OPTISCALER_ARCHIVE_ASSET["name"],
        "source_version": OPTISCALER_ARCHIVE_ASSET["version"],
        "uses_archive_native": True,
        "extra_files": [],
    },
    "rdna34-official-411": {
        "label": "4.1.1 driver override / RDNA3-4",
        "dir_name": "fsr4-rdna3-4-official-411",
        "sha256": "d0dcccc74a43c44ba435b7a369b456e0970d8a4464e4bd683119b374f2c9fb46",
        "source_asset_name": OPTISCALER_ARCHIVE_ASSET["name"],
        "source_version": OPTISCALER_ARCHIVE_ASSET["version"],
        "uses_archive_native": True,
        "extra_files": [
            {
                "name": FSR4_DRIVER_OVERRIDE_FILENAME,
                "sha256": FSR4_OFFICIAL_411_ASSET["sha256"],
                "source_asset_name": FSR4_OFFICIAL_411_ASSET["name"],
                "source_version": FSR4_OFFICIAL_411_ASSET["version"],
            }
        ],
        "config_overrides": {},
    },
    "rdna2-valve-411-pre10": {
        "label": "4.1.1 Valve RDNA2 compatibility",
        "dir_name": "fsr4-rdna2-valve-411-pre10",
        "sha256": "d0dcccc74a43c44ba435b7a369b456e0970d8a4464e4bd683119b374f2c9fb46",
        "source_asset_name": OPTISCALER_ARCHIVE_ASSET["name"],
        "source_version": OPTISCALER_ARCHIVE_ASSET["version"],
        "uses_archive_native": True,
        "injector": {
            "name": "OptiScaler.dll",
            "sha256": OPTISCALER_PRE10_ASSET["sha256"],
            "source_asset_name": OPTISCALER_PRE10_ASSET["name"],
            "source_version": OPTISCALER_PRE10_ASSET["version"],
        },
        "extra_files": [
            {
                "name": FSR4_DRIVER_OVERRIDE_FILENAME,
                "sha256": FSR4_VALVE_411_ASSET["sha256"],
                "source_asset_name": FSR4_VALVE_411_ASSET["name"],
                "source_version": FSR4_VALVE_411_ASSET["version"],
            },
            {
                "name": "amdxc64.dll",
                "sha256": AMDXC64_RDNA2_ASSET["sha256"],
                "source_asset_name": AMDXC64_RDNA2_ASSET["name"],
                "source_version": AMDXC64_RDNA2_ASSET["version"],
            },
        ],
        "config_overrides": {
            "FSR.Fsr4ForceModel": "2",
            "Plugins.LoadCustomAmdxc64OnRdna2": "true",
        },
    },
}

VARIANT_EXTRA_FILENAMES = sorted(
    {
        extra_file["name"]
        for variant in FSR4_VARIANTS.values()
        for extra_file in variant.get("extra_files", [])
    }
)

PROXY_DLL_BACKUPS = [
    "dxgi.dll",
    "winmm.dll",
    "dbghelp.dll",
    "version.dll",
    "wininet.dll",
    "winhttp.dll",
    "OptiScaler.asi",
]
VALID_DLL_NAMES = set(PROXY_DLL_BACKUPS)

INJECTOR_FILENAMES = [
    *PROXY_DLL_BACKUPS,
    "nvngx.dll",
    "_nvngx.dll",
    "nvngx-wrapper.dll",
    "dlss-enabler.dll",
    "OptiScaler.dll",
]

ORIGINAL_DLL_BACKUPS = [
    "d3dcompiler_47.dll",
    "amd_fidelityfx_dx12.dll",
    "amd_fidelityfx_framegeneration_dx12.dll",
    FSR4_UPSCALER_FILENAME,
    FSR4_DRIVER_OVERRIDE_FILENAME,
    "amdxc64.dll",
    "amd_fidelityfx_vk.dll",
]

RESTORABLE_BACKUP_FILES = [
    *PROXY_DLL_BACKUPS,
    *ORIGINAL_DLL_BACKUPS,
]

SUPPORT_FILES = [
    "libxess.dll",
    "libxess_dx11.dll",
    "libxess_fg.dll",
    "libxell.dll",
    "amd_fidelityfx_dx12.dll",
    "amd_fidelityfx_framegeneration_dx12.dll",
    "amd_fidelityfx_vk.dll",
    "dlssg_to_fsr3_amd_is_better.dll",
    "fakenvapi.dll",
    "fakenvapi.ini",
]

MARKER_FILENAME = "FRAMEGEN_PATCH"
MANIFEST_SCHEMA_VERSION = 2
BACKUP_DIRECTORY_NAME = ".framegen-backups"
