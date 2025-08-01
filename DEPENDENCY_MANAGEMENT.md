# Third-Party Dependency Management in GitHub Actions

## Overview

This document outlines different approaches for managing third-party dependencies in GitHub Actions, specifically for the `sldl` binary from the `slsk-batchdl` repository.

## Current Issue

The build was failing with "Could not get latest slsk-batchdl tag" due to:

1. **Rate Limiting**: GitHub API has rate limits for unauthenticated requests
2. **Fragile Parsing**: Using `grep` and `cut` is brittle and prone to failure
3. **No Fallback**: No backup mechanism when API calls fail

## Approaches Implemented

### 1. Multi-Method Fallback Approach (Current)

**Features:**

- Authenticated API access using `github.token`
- Fallback to unauthenticated API
- Hardcoded fallback version as last resort
- Retry logic for downloads
- Proper error handling and verification

**Code:**

```yaml
- name: Download and Extract slsk-batchdl
  run: |
    # Method 1: Authenticated API access
    if [ -n "${{ github.token }}" ]; then
      LATEST_TAG=$(curl -s -H "Authorization: token ${{ github.token }}" \
        https://api.github.com/repos/fiso64/slsk-batchdl/releases/latest | \
        jq -r '.tag_name' 2>/dev/null)
    fi

    # Method 2: Unauthenticated fallback
    if [ -z "$LATEST_TAG" ] || [ "$LATEST_TAG" = "null" ]; then
      LATEST_TAG=$(curl -s https://api.github.com/repos/fiso64/slsk-batchdl/releases/latest | \
        jq -r '.tag_name' 2>/dev/null)
    fi

    # Method 3: Hardcoded fallback
    if [ -z "$LATEST_TAG" ] || [ "$LATEST_TAG" = "null" ]; then
      LATEST_TAG="v2.4.7"
    fi
```

**Pros:**

- Robust with multiple fallbacks
- Uses proper JSON parsing with `jq`
- Handles rate limiting gracefully
- Includes retry logic

**Cons:**

- More complex code
- Requires `jq` (available in GitHub Actions runners)

### 2. GitHub Action Approach (Alternative)

**Features:**

- Uses dedicated `robinraju/release-downloader@v1.9` action
- Built-in authentication and error handling
- Simpler configuration

**Code:**

```yaml
- name: Download slsk-batchdl using GitHub Action
  uses: robinraju/release-downloader@v1.9
  with:
    repository: 'fiso64/slsk-batchdl'
    tag: 'latest'
    fileName: 'sldl_osx-${{ matrix.arch }}.zip'
    tarBall: false
    zipBall: false
    out-file-path: '.'
    access-token: ${{ github.token }}
```

**Pros:**

- Simpler configuration
- Built-in error handling
- No need for custom parsing
- Handles authentication automatically

**Cons:**

- Dependency on third-party action
- Less control over the process
- May not handle all edge cases

### 3. Caching Approach (Future Enhancement)

**Features:**

- Cache downloaded binaries between builds
- Reduce API calls and download time
- Version-based cache keys

**Code:**

```yaml
- name: Cache sldl binary
  uses: actions/cache@v3
  with:
    path: bin/sldl
    key: sldl-${{ matrix.arch }}-${{ hashFiles('**/sldl-version.txt') }}
    restore-keys: |
      sldl-${{ matrix.arch }}-
```

## Best Practices

### 1. Authentication

- Always use `github.token` for API access when possible
- Provides higher rate limits (5000 requests/hour vs 60 for unauthenticated)

### 2. Error Handling

- Implement multiple fallback methods
- Use proper exit codes and error messages
- Verify downloaded files before proceeding

### 3. Parsing

- Use `jq` for JSON parsing instead of `grep`/`cut`
- More reliable and handles edge cases better
- Available in GitHub Actions runners by default

### 4. Retry Logic

- Implement retry mechanisms for network operations
- Use exponential backoff for better reliability
- Set reasonable timeout values

### 5. Verification

- Always verify downloaded binaries
- Check file permissions and executability
- Test basic functionality (e.g., `--version` flag)

## Recommended Approach

For this project, the **Multi-Method Fallback Approach** is recommended because:

1. **Reliability**: Multiple fallback methods ensure builds don't fail
2. **Control**: Full control over the download and verification process
3. **Transparency**: Clear logging of what's happening at each step
4. **Maintainability**: Easy to update fallback versions when needed

## Monitoring and Maintenance

### Version Tracking

- Keep fallback version updated with latest stable release
- Monitor for new releases of `slsk-batchdl`
- Update hardcoded fallback version periodically

### Error Monitoring

- Watch for build failures related to dependency downloads
- Monitor rate limiting issues
- Track download success rates

### Alternative Sources

Consider these additional approaches for future enhancement:

1. **GitHub Packages**: Host sldl as a GitHub Package
2. **Docker Hub**: Containerize the build environment with pre-downloaded dependencies
3. **Self-Hosted Runners**: Use self-hosted runners with cached dependencies
4. **Release Assets**: Include sldl as a release asset in this repository

## Troubleshooting

### Common Issues

1. **Rate Limiting**

   - Solution: Use authenticated API access
   - Fallback: Implement retry logic with delays

2. **Parsing Failures**

   - Solution: Use `jq` instead of `grep`/`cut`
   - Fallback: Hardcoded version

3. **Download Failures**

   - Solution: Implement retry logic
   - Fallback: Use cached version or hardcoded fallback

4. **Binary Verification Failures**
   - Check file permissions
   - Verify architecture compatibility
   - Test with `--version` flag

### Debug Commands

```bash
# Test API access
curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/fiso64/slsk-batchdl/releases/latest | jq '.'

# Test download URL
curl -I "https://github.com/fiso64/slsk-batchdl/releases/download/v2.4.7/sldl_osx-x64.zip"

# Verify binary
file bin/sldl
bin/sldl --version
```

## Conclusion

The implemented multi-method fallback approach provides the best balance of reliability, control, and maintainability for managing the sldl dependency in GitHub Actions. The approach handles rate limiting, provides multiple fallbacks, and includes proper error handling and verification.
