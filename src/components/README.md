# Components Structure

This directory contains the organized component structure for the Decky Framegen plugin.

## Component Hierarchy

### Main Orchestrator
- **`OptiScalerControls.tsx`** - Main component that orchestrates all OptiScaler functionality and state management

### Sub-components (Logical Sections)
- **`InstallationStatus.tsx`** - Shows installation status and setup button when mod is not installed
- **`OptiScalerHeader.tsx`** - Displays the OptiScaler logo/image when installed
- **`ClipboardCommands.tsx`** - Contains the patch/unpatch command copy buttons
- **`InstructionCard.tsx`** - Shows usage instructions and help text
- **`OptiScalerWiki.tsx`** - Wiki documentation button
- **`UninstallButton.tsx`** - Red remove/uninstall button

### Utility Components
- **`SmartClipboardButton.tsx`** - Reusable clipboard copy button component
- **`ResultDisplay.tsx`** - Display component for operation results

### Other Components
- **`InstalledGamesSection.tsx`** - Games section component (currently commented out)

## State Management

All state is managed in the main `OptiScalerControls` component:
- `pathExists` - Whether the mod is installed
- `installing` - Installation progress state
- `uninstalling` - Uninstallation progress state
- `installResult` - Result of installation operation
- `uninstallResult` - Result of uninstallation operation

## Component Flow

1. **Not Installed State**: Shows `InstallationStatus` with setup button
2. **Installed State**: Shows all components in order:
   - OptiScaler header image
   - Clipboard command buttons
   - Instruction card
   - Wiki button
   - Uninstall button (red)

## Benefits of This Structure

- **Separation of Concerns**: Each component has a single responsibility
- **Reusability**: Components can be easily reused or rearranged
- **Maintainability**: Easier to find and modify specific functionality
- **Testability**: Smaller components are easier to test
- **State Management**: Centralized state in the orchestrator component
- **Clean Imports**: Barrel exports through `index.ts` for cleaner imports

## Clean Architecture

All legacy components have been removed and replaced with this organized structure. The codebase is now clean and follows modern React patterns.
