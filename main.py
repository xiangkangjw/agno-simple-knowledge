#!/usr/bin/env python3
"""Legacy launcher retained for compatibility.

The project now runs through the Tauri shell. Use `npm run tauri:dev` during
development or `npm run tauri:build` for production builds.
"""

if __name__ == "__main__":
    raise SystemExit(
        "The PyQt UI has been removed. Launch the Tauri app with "
        "`npm run tauri:dev`."
    )
