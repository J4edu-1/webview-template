#!/usr/bin/env python3
"""
inject_config.py
Reads a JSON configuration and replaces placeholders in all template files.
Handles package directory renaming and logo/splash injection.
"""

import json
import os
import sys
import shutil
import base64
import urllib.request

def main():
    if len(sys.argv) < 2:
        print("Usage: inject_config.py <config_json_string_or_file>")
        sys.exit(1)

    # Parse config
    config_input = sys.argv[1]
    if os.path.isfile(config_input):
        with open(config_input, 'r') as f:
            config = json.load(f)
    else:
        config = json.loads(config_input)

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"Project root: {project_root}")
    print(f"Config: {json.dumps(config, indent=2)}")

    # ===== BUILD PLACEHOLDERS MAP =====
    package_name = config.get("package_name", "com.example.app")
    permissions = config.get("permissions", [])
    features = []

    # Build permissions block
    perm_lines = []
    for p in permissions:
        perm_lines.append(f'    <uses-permission android:name="android.permission.{p}" />')
        if p == "CAMERA":
            features.append('    <uses-feature android:name="android.hardware.camera" android:required="false" />')
        elif p == "RECORD_AUDIO":
            features.append('    <uses-feature android:name="android.hardware.microphone" android:required="false" />')
        elif p in ("ACCESS_FINE_LOCATION", "ACCESS_COARSE_LOCATION"):
            features.append('    <uses-feature android:name="android.hardware.location" android:required="false" />')

    permissions_block = "\n".join(perm_lines)
    features_block = "\n".join(features)

    # Min SDK
    min_sdk = config.get("min_sdk", 26)

    # Determine cleartext traffic
    https_only = config.get("https_only", True)
    cleartext = "false" if https_only else "true"

    # Orientation mapping
    orientation_map = {
        "portrait": "portrait",
        "landscape": "landscape",
        "auto": "unspecified"
    }
    orientation = orientation_map.get(config.get("orientation", "portrait"), "portrait")

    placeholders = {
        "{{APP_NAME}}": config.get("app_name", "My App"),
        "{{PACKAGE_NAME}}": package_name,
        "{{BASE_URL}}": config.get("base_url", "https://example.com"),
        "{{VERSION_CODE}}": str(config.get("version_code", 1)),
        "{{VERSION_NAME}}": config.get("version_name", "1.0.0"),
        "{{MIN_SDK}}": str(min_sdk),
        "{{PERMISSIONS_BLOCK}}": permissions_block,
        "{{FEATURES_BLOCK}}": features_block,
        "{{CLEARTEXT_TRAFFIC}}": cleartext,
        "{{SCREEN_ORIENTATION}}": orientation,
        "{{JS_ENABLED}}": str(config.get("js_enabled", True)).lower(),
        "{{DOM_STORAGE}}": str(config.get("dom_storage", True)).lower(),
        "{{CACHE_ENABLED}}": str(config.get("cache_enabled", True)).lower(),
        "{{FILE_UPLOAD}}": str(config.get("file_upload", True)).lower(),
        "{{FILE_DOWNLOAD}}": str(config.get("file_download", True)).lower(),
        "{{CUSTOM_USER_AGENT}}": config.get("custom_user_agent", ""),
        "{{FULLSCREEN}}": str(config.get("fullscreen", False)).lower(),
        "{{EXTERNAL_NAV}}": str(config.get("external_nav", True)).lower(),
        "{{PULL_TO_REFRESH}}": str(config.get("pull_to_refresh", True)).lower(),
        "{{LOADING_BAR_ENABLED}}": str(config.get("loading_bar_enabled", True)).lower(),
        "{{LOADING_BAR_TYPE}}": config.get("loading_bar_type", "top_bar"),
        "{{HTTPS_ONLY}}": str(https_only).lower(),
        "{{OFFLINE_MODE}}": config.get("offline_mode", "html"),
        "{{SPLASH_DURATION}}": str(config.get("splash_duration", 1500)),
        "{{COLOR_PRIMARY}}": config.get("color_primary", "#1976D2"),
        "{{COLOR_PRIMARY_DARK}}": config.get("color_primary_dark", "#0D47A1"),
        "{{COLOR_ACCENT}}": config.get("color_accent", "#FF6D00"),
        "{{COLOR_SPLASH_BG}}": config.get("color_splash_bg", "#FFFFFF"),
    }

    # ===== PROCESS TEMPLATE FILES =====
    template_extensions = ['.template']
    for root, dirs, files in os.walk(project_root):
        # Skip hidden directories and scripts
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != 'scripts']
        for fname in files:
            if any(fname.endswith(ext) for ext in template_extensions):
                template_path = os.path.join(root, fname)
                output_path = template_path.replace('.template', '')

                with open(template_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                for placeholder, value in placeholders.items():
                    content = content.replace(placeholder, value)

                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(content)

                # Remove template file
                os.remove(template_path)
                print(f"Processed: {template_path} -> {output_path}")

    # ===== RENAME PACKAGE DIRECTORY =====
    # Move from com/template/app to the actual package path
    old_java_dir = os.path.join(project_root, "app", "src", "main", "java", "com", "template", "app")
    package_path = package_name.replace(".", os.sep)
    new_java_dir = os.path.join(project_root, "app", "src", "main", "java", package_path)

    if os.path.exists(old_java_dir):
        os.makedirs(new_java_dir, exist_ok=True)
        for f in os.listdir(old_java_dir):
            src = os.path.join(old_java_dir, f)
            dst = os.path.join(new_java_dir, f)
            shutil.move(src, dst)
            print(f"Moved: {src} -> {dst}")

        # Cleanup old dirs
        cleanup = os.path.join(project_root, "app", "src", "main", "java", "com", "template")
        shutil.rmtree(cleanup, ignore_errors=True)

    # ===== DOWNLOAD AND INJECT LOGO =====
    logo_url = config.get("logo_url", "")
    if logo_url:
        print(f"Downloading logo from: {logo_url}")
        try:
            mipmap_sizes = {
                "mipmap-mdpi": 48,
                "mipmap-hdpi": 72,
                "mipmap-xhdpi": 96,
                "mipmap-xxhdpi": 144,
                "mipmap-xxxhdpi": 192,
            }
            drawable_dir = os.path.join(project_root, "app", "src", "main", "res", "drawable")
            os.makedirs(drawable_dir, exist_ok=True)

            # Download to drawable for splash
            logo_path = os.path.join(drawable_dir, "splash_logo.png")
            urllib.request.urlretrieve(logo_url, logo_path)
            print(f"Logo saved to drawable: {logo_path}")

            # Copy to all mipmap dirs
            for mipmap_dir_name in mipmap_sizes:
                mipmap_dir = os.path.join(project_root, "app", "src", "main", "res", mipmap_dir_name)
                os.makedirs(mipmap_dir, exist_ok=True)
                for icon_name in ["ic_launcher.png", "ic_launcher_round.png"]:
                    dst = os.path.join(mipmap_dir, icon_name)
                    shutil.copy2(logo_path, dst)
                    print(f"Logo copied to: {dst}")
        except Exception as e:
            print(f"WARNING: Failed to download logo: {e}")
    else:
        # Create a placeholder drawable directory with a default splash
        drawable_dir = os.path.join(project_root, "app", "src", "main", "res", "drawable")
        os.makedirs(drawable_dir, exist_ok=True)
        # Use default mipmap icons (they won't exist without logo, so create minimal placeholder)
        for mipmap_dir_name in ["mipmap-mdpi", "mipmap-hdpi", "mipmap-xhdpi", "mipmap-xxhdpi", "mipmap-xxxhdpi"]:
            mipmap_dir = os.path.join(project_root, "app", "src", "main", "res", mipmap_dir_name)
            os.makedirs(mipmap_dir, exist_ok=True)

    print("\n✅ Configuration injection complete!")

if __name__ == "__main__":
    main()
