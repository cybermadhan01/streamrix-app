import os
import sys
import shutil
import subprocess
import zipfile
from PIL import Image

# CI-safe tool discovery: everything comes from the runner environment, never
# from a hardcoded developer-machine path.
ANDROID_SDK = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT") or "/usr/local/lib/android/sdk"
BUILD_TOOLS_VERSION = os.environ.get("ANDROID_BUILD_TOOLS", "34.0.0")
BUILD_TOOLS_DIR = os.path.join(ANDROID_SDK, "build-tools", BUILD_TOOLS_VERSION)
AAPT2 = os.path.join(BUILD_TOOLS_DIR, "aapt2" if os.name != "nt" else "aapt2.exe")
D8 = os.path.join(BUILD_TOOLS_DIR, "d8" if os.name != "nt" else "d8.bat")
ZIPALIGN = os.path.join(BUILD_TOOLS_DIR, "zipalign" if os.name != "nt" else "zipalign.exe")
APKSIGNER = os.path.join(BUILD_TOOLS_DIR, "apksigner" if os.name != "nt" else "apksigner.bat")
ANDROID_JAR = os.path.join(ANDROID_SDK, "platforms", "android-34", "android.jar")
JAVA_HOME = os.environ.get("JAVA_HOME", "")
JAVAC = os.path.join(JAVA_HOME, "bin", "javac" + (".exe" if os.name == "nt" else ""))
KEYTOOL = os.path.join(JAVA_HOME, "bin", "keytool" + (".exe" if os.name == "nt" else ""))

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "android")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, "download")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

PACKAGE_NAME = "com.streamrix.app"
APP_NAME = "StreamRix"
TARGET_URL = "https://streamrix.site/player.html"

def check_tools():
    for name, path in [
        ("AAPT2", AAPT2), ("D8", D8), ("ZIPALIGN", ZIPALIGN),
        ("APKSIGNER", APKSIGNER), ("ANDROID_JAR", ANDROID_JAR),
        ("JAVAC", JAVAC), ("KEYTOOL", KEYTOOL)
    ]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing required tool: {name} at {path}")
    print("[✓] All Android build tools verified.")

def prepare_directories():
    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)
    
    # Resource directories for multi-density icons & layouts
    densities = ["drawable", "drawable-nodpi", "drawable-xhdpi", "mipmap-mdpi", "mipmap-hdpi", "mipmap-xhdpi", "mipmap-xxhdpi", "mipmap-xxxhdpi"]
    for d in densities:
        os.makedirs(os.path.join(BUILD_DIR, "res", d), exist_ok=True)
    
    os.makedirs(os.path.join(BUILD_DIR, "res", "values"), exist_ok=True)
    os.makedirs(os.path.join(BUILD_DIR, "res", "layout"), exist_ok=True)
    os.makedirs(os.path.join(BUILD_DIR, "src", "com", "streamrix", "app"), exist_ok=True)
    os.makedirs(os.path.join(BUILD_DIR, "obj"), exist_ok=True)
    os.makedirs(os.path.join(BUILD_DIR, "bin"), exist_ok=True)
    os.makedirs(os.path.join(BUILD_DIR, "assets", "offline"), exist_ok=True)
    os.makedirs(os.path.join(BUILD_DIR, "assets", "branding"), exist_ok=True)
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    print("[✓] Build directories and asset trees initialized.")

def populate_resources():
    print("[>] Populating Android multi-density icon suite & splash resources...")
    src_512 = os.path.join(ASSETS_DIR, "icons", "icon-512.png")
    if not os.path.exists(src_512):
        src_512 = os.path.join(ASSETS_DIR, "icons", "streamrix-icon.png")
    if os.path.exists(src_512):
        icon_img = Image.open(src_512).convert("RGBA")
    else:
        # No source assets in this repo — synthesize a clean placeholder icon.
        icon_img = Image.new("RGBA", (512, 512), (7, 9, 14, 255))
    
    # Standard densities
    density_map = {
        "mipmap-mdpi": 48,
        "mipmap-hdpi": 72,
        "mipmap-xhdpi": 96,
        "mipmap-xxhdpi": 144,
        "mipmap-xxxhdpi": 192,
        "drawable": 192,
        "drawable-xhdpi": 192
    }
    for folder, sz in density_map.items():
        res = icon_img.resize((sz, sz), Image.Resampling.LANCZOS)
        res.save(os.path.join(BUILD_DIR, "res", folder, "ic_launcher.png"), "PNG")

    # Android TV Leanback Banner (320x180 and 1920x1080)
    tv_320 = os.path.join(ASSETS_DIR, "branding", "tv_banner_320.png")
    tv_1080 = os.path.join(ASSETS_DIR, "branding", "tv_banner_1080p.png")
    if os.path.exists(tv_320):
        shutil.copy2(tv_320, os.path.join(BUILD_DIR, "res", "drawable", "tv_banner.png"))
    else:
        from PIL import ImageDraw
        banner = Image.new("RGB", (320, 180), (7, 9, 14))
        ImageDraw.Draw(banner).text((24, 82), "StreamRix", fill=(255, 255, 255))
        banner.save(os.path.join(BUILD_DIR, "res", "drawable", "tv_banner.png"), "PNG")
    if os.path.exists(tv_1080):
        shutil.copy2(tv_1080, os.path.join(BUILD_DIR, "res", "drawable-nodpi", "tv_banner.png"))

    # High-Res Splash Screen
    splash_portrait = os.path.join(ASSETS_DIR, "branding", "splash_portrait.png")
    if os.path.exists(splash_portrait):
        shutil.copy2(splash_portrait, os.path.join(BUILD_DIR, "res", "drawable-nodpi", "splash_bg.png"))
    
    # Logo for Splash Activity (downloaded from the live site by CI when available)
    splash_logo = os.path.join(PROJECT_ROOT, "STREAMRIX-LOGO.png")
    if os.path.exists(splash_logo):
        shutil.copy2(splash_logo, os.path.join(BUILD_DIR, "res", "drawable", "logo_splash.png"))
    else:
        icon_img.save(os.path.join(BUILD_DIR, "res", "drawable", "logo_splash.png"), "PNG")

    # Bundle Offline Fallback Engine into APK assets (optional)
    offline_src = os.path.join(ASSETS_DIR, "offline")
    offline_dst = os.path.join(BUILD_DIR, "assets", "offline")
    if os.path.isdir(offline_src):
        for f in os.listdir(offline_src):
            shutil.copy2(os.path.join(offline_src, f), os.path.join(offline_dst, f))

    # Bundle Cinematic Artwork into APK assets (optional)
    branding_src = os.path.join(ASSETS_DIR, "branding")
    branding_dst = os.path.join(BUILD_DIR, "assets", "branding")
    if os.path.isdir(branding_src):
        for f in os.listdir(branding_src):
            shutil.copy2(os.path.join(branding_src, f), os.path.join(branding_dst, f))

    # Also bundle high-res images from assets/images for rich local cache
    images_src = os.path.join(ASSETS_DIR, "images")
    if os.path.exists(images_src):
        images_dst = os.path.join(BUILD_DIR, "assets", "images")
        os.makedirs(images_dst, exist_ok=True)
        for f in os.listdir(images_src):
            if f.endswith((".png", ".jpg", ".webp")):
                shutil.copy2(os.path.join(images_src, f), os.path.join(images_dst, f))

    print("[✓] Multi-density icon suite, TV banners, and bundled assets ready.")

def write_manifest():
    manifest_content = f"""<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="{PACKAGE_NAME}"
    android:versionCode="1"
    android:versionName="1.0.0">

    <!-- Modern Android 14 (API 34) Target: Prevents Play Protect "older version" blocks -->
    <uses-sdk
        android:minSdkVersion="24"
        android:targetSdkVersion="34" />

    <!-- Pure Streaming Permissions (Normal permissions - NEVER prompts user for scary access) -->
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.ACCESS_NETWORK_STATE" />
    <uses-permission android:name="android.permission.WAKE_LOCK" />

    <!-- Leanback TV / Google TV / Fire TV Support -->
    <uses-feature android:name="android.hardware.touchscreen" android:required="false" />
    <uses-feature android:name="android.software.leanback" android:required="false" />

    <application
        android:label="@string/app_name"
        android:icon="@drawable/ic_launcher"
        android:banner="@drawable/tv_banner"
        android:hardwareAccelerated="true"
        android:largeHeap="true"
        android:usesCleartextTraffic="true"
        android:theme="@style/AppTheme">

        <activity
            android:name=".MainActivity"
            android:configChanges="orientation|screenSize|screenLayout|smallestScreenSize|keyboard|keyboardHidden|navigation"
            android:screenOrientation="user"
            android:launchMode="singleTask"
            android:exported="true">
            
            <!-- Standard Android Launcher (Phone, Tablet) -->
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>

            <!-- Android TV / FireStick Leanback Launcher -->
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LEANBACK_LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
"""
    with open(os.path.join(BUILD_DIR, "AndroidManifest.xml"), "w", encoding="utf-8") as f:
        f.write(manifest_content)

def write_values():
    strings_content = f"""<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">{APP_NAME}</string>
    <string name="splash_connecting">CONNECTING TO STREAMRIX</string>
</resources>
"""
    with open(os.path.join(BUILD_DIR, "res", "values", "strings.xml"), "w", encoding="utf-8") as f:
        f.write(strings_content)

    styles_content = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="@android:style/Theme.NoTitleBar.Fullscreen">
        <item name="android:windowBackground">@android:color/black</item>
        <item name="android:colorBackground">#050508</item>
    </style>
</resources>
"""
    with open(os.path.join(BUILD_DIR, "res", "values", "styles.xml"), "w", encoding="utf-8") as f:
        f.write(styles_content)

def write_layout():
    layout_content = """<?xml version="1.0" encoding="utf-8"?>
<FrameLayout xmlns:android="http://schemas.android.com/apk/res/android"
    android:id="@+id/rootContainer"
    android:layout_width="match_parent"
    android:layout_height="match_parent"
    android:background="#050508">

    <!-- Primary Video Surface -->
    <WebView
        android:id="@+id/appWebView"
        android:layout_width="match_parent"
        android:layout_height="match_parent"
        android:background="#050508" />

    <!-- Sleek Native Cinematic Splash Surface (Visible Instantly, 0 Delay) -->
    <RelativeLayout
        android:id="@+id/splashContainer"
        android:layout_width="match_parent"
        android:layout_height="match_parent"
        android:background="#050508"
        android:clickable="true"
        android:focusable="true">

        <ImageView
            android:id="@+id/splashLogo"
            android:layout_width="260dp"
            android:layout_height="80dp"
            android:layout_centerInParent="true"
            android:src="@drawable/logo_splash"
            android:scaleType="fitCenter"
            android:contentDescription="StreamRix" />

        <ProgressBar
            android:id="@+id/splashProgress"
            android:layout_width="32dp"
            android:layout_height="32dp"
            android:layout_below="@id/splashLogo"
            android:layout_centerHorizontal="true"
            android:layout_marginTop="28dp"
            android:indeterminate="true" />

        <TextView
            android:id="@+id/splashText"
            android:layout_width="wrap_content"
            android:layout_height="wrap_content"
            android:layout_below="@id/splashProgress"
            android:layout_centerHorizontal="true"
            android:layout_marginTop="16dp"
            android:text="@string/splash_connecting"
            android:textColor="#557799"
            android:textSize="11sp"
            android:letterSpacing="0.15" />
    </RelativeLayout>
</FrameLayout>
"""
    with open(os.path.join(BUILD_DIR, "res", "layout", "activity_main.xml"), "w", encoding="utf-8") as f:
        f.write(layout_content)
    print("[✓] Layout activity_main.xml written.")

def write_java():
    java_content = f"""package com.streamrix.app;

import android.app.Activity;
import android.app.UiModeManager;
import android.content.pm.ActivityInfo;
import android.content.res.Configuration;
import android.os.Bundle;
import android.view.View;
import android.view.KeyEvent;
import android.view.WindowManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceError;
import android.webkit.JavascriptInterface;
import android.widget.RelativeLayout;
import android.graphics.Color;

public class MainActivity extends Activity {{
    private WebView mWebView;
    private RelativeLayout mSplashContainer;
    private boolean mHasLoadedFirstPage = false;

    public static class AndroidBridge {{
        private final MainActivity mActivity;
        public AndroidBridge(MainActivity activity) {{
            this.mActivity = activity;
        }}

        @JavascriptInterface
        public void setOrientation(String mode) {{
            if (mActivity != null) {{
                mActivity.changeOrientation(mode);
            }}
        }}
    }}

    public static class OrientationRunnable implements Runnable {{
        private final MainActivity mActivity;
        private final String mMode;

        public OrientationRunnable(MainActivity activity, String mode) {{
            this.mActivity = activity;
            this.mMode = mode;
        }}

        @Override
        public void run() {{
            if (mActivity == null) return;
            try {{
                UiModeManager uiModeManager = (UiModeManager) mActivity.getSystemService(UI_MODE_SERVICE);
                if (uiModeManager != null && uiModeManager.getCurrentModeType() == Configuration.UI_MODE_TYPE_TELEVISION) {{
                    mActivity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
                    return;
                }}

                if ("landscape".equalsIgnoreCase(mMode)) {{
                    mActivity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_LANDSCAPE);
                }} else if ("portrait".equalsIgnoreCase(mMode)) {{
                    mActivity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_SENSOR_PORTRAIT);
                }} else {{
                    mActivity.setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_USER);
                }}
            }} catch (Exception ignored) {{}}
        }}
    }}

    public void changeOrientation(final String mode) {{
        runOnUiThread(new OrientationRunnable(this, mode));
    }}

    public static class AppWebViewClient extends WebViewClient {{
        private MainActivity mActivity;

        public AppWebViewClient(MainActivity activity) {{
            this.mActivity = activity;
        }}

        @Override
        public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {{
            return false;
        }}

        @Override
        public void onPageFinished(WebView view, String url) {{
            super.onPageFinished(view, url);
            if (mActivity != null && !mActivity.mHasLoadedFirstPage) {{
                mActivity.mHasLoadedFirstPage = true;
                mActivity.dismissSplash();
            }}
        }}

        @Override
        public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {{
            if (request.isForMainFrame()) {{
                // Graceful Offline Fallback Engine: load native asset
                view.loadUrl("file:///android_asset/offline/index.html");
                if (mActivity != null) {{
                    mActivity.dismissSplash();
                }}
            }}
        }}
    }}

    @Override
    protected void onCreate(Bundle savedInstanceState) {{
        super.onCreate(savedInstanceState);

        // Television devices lock to landscape; phones/tablets start in user orientation
        try {{
            UiModeManager uiModeManager = (UiModeManager) getSystemService(UI_MODE_SERVICE);
            if (uiModeManager != null && uiModeManager.getCurrentModeType() == Configuration.UI_MODE_TYPE_TELEVISION) {{
                setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
            }} else {{
                setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_USER);
            }}
        }} catch (Exception ignored) {{}}

        // Hardware acceleration & screen keep awake during streams
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_HARDWARE_ACCELERATED);

        hideSystemUI();
        setContentView(R.layout.activity_main);

        mSplashContainer = (RelativeLayout) findViewById(R.id.splashContainer);
        mWebView = (WebView) findViewById(R.id.appWebView);
        mWebView.setBackgroundColor(Color.parseColor("#050508"));

        WebSettings settings = mWebView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setLoadsImagesAutomatically(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);

        String defaultUA = settings.getUserAgentString();
        settings.setUserAgentString(defaultUA + " StreamRixApp/1.0.0 (Native Sideload Shell)");

        mWebView.setWebViewClient(new AppWebViewClient(this));
        mWebView.setWebChromeClient(new WebChromeClient());
        mWebView.addJavascriptInterface(new AndroidBridge(this), "AndroidBridge");

        // Connect directly to live sovereign edge
        mWebView.loadUrl("{TARGET_URL}");
    }}

    public static class HideSplashRunnable implements Runnable {{
        private final RelativeLayout mSplash;
        public HideSplashRunnable(RelativeLayout splash) {{
            this.mSplash = splash;
        }}
        @Override
        public void run() {{
            if (mSplash != null) {{
                mSplash.setVisibility(View.GONE);
            }}
        }}
    }}

    public void dismissSplash() {{
        if (mSplashContainer != null && mSplashContainer.getVisibility() == View.VISIBLE) {{
            mSplashContainer.animate()
                .alpha(0.0f)
                .setDuration(450)
                .withEndAction(new HideSplashRunnable(mSplashContainer));
        }}
    }}

    private void hideSystemUI() {{
        View decorView = getWindow().getDecorView();
        decorView.setSystemUiVisibility(
            View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE
            | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
            | View.SYSTEM_UI_FLAG_FULLSCREEN
        );
    }}

    @Override
    public void onWindowFocusChanged(boolean hasFocus) {{
        super.onWindowFocusChanged(hasFocus);
        if (hasFocus) {{
            hideSystemUI();
        }}
    }}

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {{
        if (keyCode == KeyEvent.KEYCODE_BACK) {{
            if (mWebView != null && mWebView.canGoBack()) {{
                mWebView.goBack();
                return true;
            }}
        }}
        return super.onKeyDown(keyCode, event);
    }}

    @Override
    protected void onResume() {{
        super.onResume();
        if (mWebView != null) mWebView.onResume();
    }}

    @Override
    protected void onPause() {{
        super.onPause();
        if (mWebView != null) mWebView.onPause();
    }}

    @Override
    protected void onDestroy() {{
        super.onDestroy();
        if (mWebView != null) {{
            mWebView.destroy();
        }}
    }}
}}
"""
    java_file = os.path.join(BUILD_DIR, "src", "com", "streamrix", "app", "MainActivity.java")
    with open(java_file, "w", encoding="utf-8") as f:
        f.write(java_content)
    print("[✓] Native Android MainActivity.java written.")

def run_cmd(cmd, desc):
    print(f"[>] {desc}...")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"[!] Error in {desc}:")
        print(res.stderr)
        print(res.stdout)
        sys.exit(1)

def build_apk():
    # 1. AAPT2 compile
    compiled_res = os.path.join(BUILD_DIR, "obj", "res.zip")
    run_cmd(
        f'"{AAPT2}" compile --dir "{os.path.join(BUILD_DIR, "res")}" -o "{compiled_res}"',
        "AAPT2 compile resources"
    )

    # 2. AAPT2 link
    proto_apk = os.path.join(BUILD_DIR, "bin", "proto.apk")
    r_java_dir = os.path.join(BUILD_DIR, "src")
    run_cmd(
        f'"{AAPT2}" link -I "{ANDROID_JAR}" --manifest "{os.path.join(BUILD_DIR, "AndroidManifest.xml")}" "{compiled_res}" --java "{r_java_dir}" -o "{proto_apk}" --auto-add-overlay',
        "AAPT2 link and generate R.java"
    )

    # 3. JAVAC compile
    java_sources = []
    for root, _, files in os.walk(os.path.join(BUILD_DIR, "src")):
        for f in files:
            if f.endswith(".java"):
                java_sources.append(os.path.join(root, f))
    
    classes_dir = os.path.join(BUILD_DIR, "obj", "classes")
    os.makedirs(classes_dir, exist_ok=True)
    sources_str = " ".join([f'"{s}"' for s in java_sources])
    run_cmd(
        f'"{JAVAC}" -source 1.8 -target 1.8 -bootclasspath "{ANDROID_JAR}" -d "{classes_dir}" {sources_str}',
        "Compile Java sources with javac"
    )

    # 4. D8 DEX conversion. Pack classes into classes.jar so d8 gets a valid jar input
    # (d8 rejects directories with "Unsupported source file type").
    dex_dir = os.path.join(BUILD_DIR, "bin")
    os.makedirs(dex_dir, exist_ok=True)
    classes_jar = os.path.join(BUILD_DIR, "obj", "classes.jar")
    with zipfile.ZipFile(classes_jar, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(classes_dir):
            for file in files:
                if file.endswith(".class"):
                    abs_p = os.path.join(root, file)
                    rel_p = os.path.relpath(abs_p, classes_dir).replace("\\", "/")
                    zf.write(abs_p, rel_p)

    run_cmd(
        f'"{D8}" --lib "{ANDROID_JAR}" --output "{dex_dir}" "{classes_jar}"',
        "Convert classes to DEX with d8"
    )

    # 5. Package unaligned APK with classes.dex AND full assets directory
    unaligned_apk = os.path.join(BUILD_DIR, "bin", "unaligned.apk")
    shutil.copy2(proto_apk, unaligned_apk)

    dex_path = os.path.join(dex_dir, "classes.dex")
    assets_dir = os.path.join(BUILD_DIR, "assets")

    with zipfile.ZipFile(unaligned_apk, 'a', zipfile.ZIP_DEFLATED) as z:
        z.write(dex_path, "classes.dex")
        for root, _, files in os.walk(assets_dir):
            for file in files:
                p = os.path.join(root, file)
                rel = os.path.relpath(p, BUILD_DIR)
                arcname = rel.replace("\\", "/")
                z.write(p, arcname)
    print("[✓] Injected classes.dex and rich assets into unaligned APK.")

    # 6. Zipalign (4-byte alignment)
    aligned_apk = os.path.join(BUILD_DIR, "bin", "aligned.apk")
    run_cmd(
        f'"{ZIPALIGN}" -f 4 "{unaligned_apk}" "{aligned_apk}"',
        "Zipalign APK"
    )

    # 7. Anonymous Permanent Release Keystore (Preserves SHA-256 fingerprint across all builds)
    certs_dir = os.path.join(PROJECT_ROOT, "certs")
    os.makedirs(certs_dir, exist_ok=True)
    keystore = os.path.join(certs_dir, "streamrix-release.keystore")
    if not os.path.exists(keystore):
        run_cmd(
            f'"{KEYTOOL}" -genkeypair -v -keystore "{keystore}" -storepass "streamrix2026" -alias "streamrix" -keypass "streamrix2026" -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=StreamRix, O=StreamRix Sovereign Entertainment, C=US"',
            "Generate anonymous release keystore"
        )

    # 8. Cryptographic Release Signing with apksigner (v1, v2, v3)
    final_apk = os.path.join(DIST_DIR, "streamrix.apk")
    run_cmd(
        f'"{APKSIGNER}" sign --ks "{keystore}" --ks-pass pass:streamrix2026 --ks-key-alias streamrix --key-pass pass:streamrix2026 --out "{final_apk}" "{aligned_apk}"',
        "Sign APK with apksigner (v1, v2, v3)"
    )

    # 9. Copy to website download folder
    website_apk = os.path.join(DOWNLOAD_DIR, "streamrix.apk")
    shutil.copy2(final_apk, website_apk)

    size_mb = os.path.getsize(final_apk) / (1024 * 1024)
    print(f"\n=================================================================")
    print(f"🎉 PRODUCTION STREAMRIX APK SUCCESSFULLY BUILT & SIGNED!")
    print(f"File: {final_apk}")
    print(f"Size: {size_mb:.2f} MB")
    print(f"Package: {PACKAGE_NAME}")
    print(f"Features: Leanback TV, 4K Splash, Multi-density Icons, Offline Engine")
    print(f"=================================================================\n")

if __name__ == "__main__":
    check_tools()
    prepare_directories()
    populate_resources()
    write_manifest()
    write_values()
    write_layout()
    write_java()
    build_apk()
