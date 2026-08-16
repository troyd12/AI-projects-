# MCP Android Connector Setup

## Quick Start

### Prerequisites
1. Install Android SDK (or just ADB): `sudo apt install adb` (Linux) or install via Android Studio
2. Enable USB Debugging on your Android phone:
   - Go to Settings > About Phone > tap "Build Number" 7 times
   - Go to Settings > Developer Options > enable "USB Debugging"
3. Connect phone via USB and confirm the debugging prompt on the device
4. Verify connection: `adb devices` (should show your device)

### MCP Server (Mobile MCP)
The `.mcp.json` in this repo configures **Mobile MCP** by Mobile Next, which provides:
- Take screenshots of the device screen
- Read UI element tree (buttons, text, inputs)
- Tap at coordinates / on elements
- Swipe gestures
- Type text input
- Launch and close apps
- File management

### Usage with Claude Desktop
Copy the config to your Claude Desktop settings:
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

### Usage with Claude Code
The `.mcp.json` file in this repo is automatically picked up by Claude Code.

## Alternative MCP Android Connectors

| Tool | Best For | Install |
|------|----------|--------|
| [Mobile MCP](https://github.com/mobile-next/mobile-mcp) | General use, easiest setup | `npx -y @mobilenext/mobile-mcp@latest` |
| [Aster MCP](https://github.com/satyajiit/aster-mcp) | On-device, no computer needed | Companion Android app |
| [replicant-mcp](https://github.com/thecombatwombat/replicant-mcp) | Android development workflows | `npm install -g replicant-mcp` |
| [android-remote-control-mcp](https://github.com/danielealbano/android-remote-control-mcp) | Remote access via tunneling | APK install on device |
