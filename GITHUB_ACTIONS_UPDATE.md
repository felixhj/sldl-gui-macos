# GitHub Actions Workflow Update

## Overview

The GitHub Actions workflow has been updated to properly bundle the `sldl` dependency with the application, matching the approach used in the Monterey build script.

## Key Changes Made

### 1. Updated sldl Download and Bundling

**Before:**

- Used `robinraju/release-downloader@v1.9` action
- Downloaded sldl to root directory
- Used `--add-binary="sldl:."` in PyInstaller

**After:**

- Direct curl download using GitHub API
- Downloads sldl to `bin/` directory
- Uses `--add-binary="bin/sldl:bin"` in PyInstaller
- Matches the expected path in code: `Path(sys._MEIPASS) / 'bin' / 'sldl'`

### 2. Fixed sldl File Naming Pattern

**Issue Found:**

- The workflow was looking for `osx-${{ matrix.arch }}.zip`
- Actual release files are named `sldl_osx-${{ matrix.arch }}.zip`

**Fix Applied:**

- Updated grep pattern to `sldl_osx-${{ matrix.arch }}.zip`
- This matches the actual release assets from slsk-batchdl

### 3. Improved Error Handling

- Added validation to ensure the correct architecture binary is found
- Added verification that sldl binary is executable and working
- Better error messages if download fails

## Separate 13.x and 14.x Builds - Analysis

**Yes, separate builds are necessary and beneficial:**

### Why Separate Builds Are Needed

1. **Architecture Differences**

   - `macos-13` (Ventura) builds for Intel (x64) architecture
   - `macos-14` (Sonoma) builds for Apple Silicon (arm64) architecture
   - Different sldl binaries are required for each architecture

2. **macOS Version Compatibility**

   - Apps built on newer macOS versions may not run on older ones
   - Ventura (13.x) and Sonoma (14.x) have different system APIs
   - Building on the target macOS version ensures maximum compatibility

3. **User Base Coverage**
   - Intel Macs are still common and need support
   - Apple Silicon Macs are the future and need native performance
   - Separate builds ensure optimal performance for each architecture

### Current Matrix Configuration

```yaml
matrix:
  include:
    - os: macos-13 # Ventura for x86_64
      arch: x64
      python-version: '3.9'
    - os: macos-14 # Sonoma for arm64 (Apple Silicon)
      arch: arm64
      python-version: '3.9'
```

This creates:

- `SoulseekDownloader-x64-ventura.dmg` (Intel Macs)
- `SoulseekDownloader-arm64-sonoma.dmg` (Apple Silicon Macs)

## Benefits of This Approach

1. **Proper Bundling**: sldl is now correctly bundled in the app bundle
2. **No External Dependencies**: Users don't need to install sldl separately
3. **Architecture Optimization**: Each build is optimized for its target architecture
4. **Wide Compatibility**: Covers both Intel and Apple Silicon Macs
5. **Future-Proof**: Easy to add more macOS versions if needed

## Testing the Changes

To test the updated workflow:

1. Create a new tag: `git tag v1.x.x`
2. Push the tag: `git push origin v1.x.x`
3. Check the GitHub Actions tab for build progress
4. Verify both DMG files are created and uploaded to the release

## Comparison with Monterey Build

The GitHub Actions workflow now matches the Monterey build script approach:

| Aspect        | Monterey Script                       | GitHub Actions                        |
| ------------- | ------------------------------------- | ------------------------------------- |
| sldl Download | curl + GitHub API                     | curl + GitHub API                     |
| sldl Location | `bin/sldl`                            | `bin/sldl`                            |
| PyInstaller   | `--add-binary="bin/sldl:bin"`         | `--add-binary="bin/sldl:bin"`         |
| Code Path     | `Path(sys._MEIPASS) / 'bin' / 'sldl'` | `Path(sys._MEIPASS) / 'bin' / 'sldl'` |

This ensures consistency between local and automated builds.

## Troubleshooting

### Common Issues

1. **sldl Download Fails**

   - **Cause**: Incorrect file naming pattern in grep
   - **Solution**: Use `sldl_osx-${{ matrix.arch }}.zip` pattern
   - **Status**: ✅ Fixed

2. **Build Cancellation**

   - **Cause**: Timeout or manual cancellation
   - **Solution**: Monitor build progress and ensure sufficient time
   - **Status**: ⚠️ Monitor

3. **Architecture Mismatch**
   - **Cause**: Wrong sldl binary for target architecture
   - **Solution**: Ensure correct `matrix.arch` mapping
   - **Status**: ✅ Working correctly
