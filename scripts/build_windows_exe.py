import os
import glob
import subprocess
import shutil
import zipfile
import urllib.request

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, "download")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "windows_native")
CSC = os.environ.get("CSC") or (
    glob.glob(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
    or glob.glob(r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe")
    or [r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"]
)[0]
ICON_PATH = os.path.join(PROJECT_ROOT, "favicon_clean.ico")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

TARGET_URL = "https://streamrix.site/player.html"

def prepare_dirs():
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def ensure_webview2_dependencies():
    """Ensure WebView2 assemblies and loader DLLs are ready in BUILD_DIR."""
    core_dll = os.path.join(BUILD_DIR, "Microsoft.Web.WebView2.Core.dll")
    winforms_dll = os.path.join(BUILD_DIR, "Microsoft.Web.WebView2.WinForms.dll")
    loader_dll = os.path.join(BUILD_DIR, "WebView2Loader.dll")

    if os.path.exists(core_dll) and os.path.exists(winforms_dll) and os.path.exists(loader_dll):
        return core_dll, winforms_dll, loader_dll

    pkg_zip = os.path.join(PROJECT_ROOT, "build", "nuget", "webview2.zip")
    if not os.path.exists(pkg_zip):
        os.makedirs(os.path.dirname(pkg_zip), exist_ok=True)
        print("[>] Downloading WebView2 NuGet package...")
        url = "https://www.nuget.org/api/v2/package/Microsoft.Web.WebView2/1.0.2592.51"
        urllib.request.urlretrieve(url, pkg_zip)

    with zipfile.ZipFile(pkg_zip, "r") as z:
        z.extract("lib/net462/Microsoft.Web.WebView2.Core.dll", BUILD_DIR)
        z.extract("lib/net462/Microsoft.Web.WebView2.WinForms.dll", BUILD_DIR)
        z.extract("runtimes/win-x64/native/WebView2Loader.dll", BUILD_DIR)

    shutil.copy2(os.path.join(BUILD_DIR, "lib", "net462", "Microsoft.Web.WebView2.Core.dll"), core_dll)
    shutil.copy2(os.path.join(BUILD_DIR, "lib", "net462", "Microsoft.Web.WebView2.WinForms.dll"), winforms_dll)
    shutil.copy2(os.path.join(BUILD_DIR, "runtimes", "win-x64", "native", "WebView2Loader.dll"), loader_dll)
    return core_dll, winforms_dll, loader_dll

def write_csharp_source():
    cs_content = r'''using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

namespace StreamRix
{
    public class MainForm : Form
    {
        [DllImport("shell32.dll", SetLastError = true)]
        static extern void SetCurrentProcessExplicitAppUserModelID([MarshalAs(UnmanagedType.LPWStr)] string AppID);

        private WebView2 webView;
        private bool isFullScreen = false;
        private FormWindowState prevWindowState;
        private FormBorderStyle prevBorderStyle;
        private const string TargetUrl = "https://streamrix.site/player.html";

        public MainForm()
        {
            try
            {
                SetCurrentProcessExplicitAppUserModelID("StreamRix.Entertainment.Cinema");
            }
            catch {}

            this.Text = "StreamRix";
            this.Size = new Size(1366, 768);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.BackColor = Color.FromArgb(7, 9, 14);

            // Set Form Icon from embedded assembly icon
            try
            {
                string exePath = Assembly.GetExecutingAssembly().Location;
                this.Icon = Icon.ExtractAssociatedIcon(exePath);
            }
            catch {}

            // Automatically ensure official desktop & start menu shortcuts exist
            EnsureDesktopShortcut();

            webView = new WebView2
            {
                Dock = DockStyle.Fill
            };
            this.Controls.Add(webView);

            this.KeyPreview = true;
            this.KeyDown += MainForm_KeyDown;
            this.Load += MainForm_Load;
        }

        private async void MainForm_Load(object sender, EventArgs e)
        {
            try
            {
                string userDataFolder = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "StreamRix", "WebViewData");
                Directory.CreateDirectory(userDataFolder);

                var env = await CoreWebView2Environment.CreateAsync(null, userDataFolder);
                await webView.EnsureCoreWebView2Async(env);

                // Configure cinema media settings
                webView.CoreWebView2.Settings.IsStatusBarEnabled = false;
                webView.CoreWebView2.Settings.AreDefaultContextMenusEnabled = false;
                webView.CoreWebView2.Settings.IsZoomControlEnabled = false;

                // Handle HTML5 video full screen
                webView.CoreWebView2.ContainsFullScreenElementChanged += (s, args) =>
                {
                    ToggleFullScreen(webView.CoreWebView2.ContainsFullScreenElement);
                };

                webView.CoreWebView2.Navigate(TargetUrl);
            }
            catch (Exception)
            {
                // Fallback directly INSIDE MainForm so StreamRix.exe NEVER terminates or hands off to external Edge!
                // This guarantees the taskbar icon, pinned app, and process identity remain 100% StreamRix at all times.
                try
                {
                    this.Controls.Remove(webView);
                    WebBrowser wb = new WebBrowser
                    {
                        Dock = DockStyle.Fill,
                        ScriptErrorsSuppressed = true
                    };
                    this.Controls.Add(wb);
                    wb.Navigate(TargetUrl);
                }
                catch {}
            }
        }

        private void MainForm_KeyDown(object sender, KeyEventArgs e)
        {
            if (e.KeyCode == Keys.F11)
            {
                ToggleFullScreen(!isFullScreen);
                e.Handled = true;
            }
            else if (e.KeyCode == Keys.Escape && isFullScreen)
            {
                ToggleFullScreen(false);
                e.Handled = true;
            }
        }

        private void ToggleFullScreen(bool fullscreen)
        {
            if (fullscreen && !isFullScreen)
            {
                prevWindowState = this.WindowState;
                prevBorderStyle = this.FormBorderStyle;

                this.FormBorderStyle = FormBorderStyle.None;
                this.WindowState = FormWindowState.Normal;
                this.WindowState = FormWindowState.Maximized;
                isFullScreen = true;
            }
            else if (!fullscreen && isFullScreen)
            {
                this.FormBorderStyle = prevBorderStyle;
                this.WindowState = prevWindowState;
                isFullScreen = false;
            }
        }

        private static void EnsureDesktopShortcut()
        {
            try
            {
                string exePath = Assembly.GetExecutingAssembly().Location;
                string exeDir = Path.GetDirectoryName(exePath);

                // 1. Desktop shortcut
                string desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
                string shortcutPath = Path.Combine(desktop, "StreamRix.lnk");
                CreateLnk(shortcutPath, exePath, exeDir);

                // 2. Start Menu shortcut (critical for Windows 10/11 taskbar pin identification)
                string startMenu = Environment.GetFolderPath(Environment.SpecialFolder.StartMenu);
                string smPrograms = Path.Combine(startMenu, "Programs");
                CreateLnk(Path.Combine(smPrograms, "StreamRix.lnk"), exePath, exeDir);

                string smFolder = Path.Combine(smPrograms, "StreamRix");
                Directory.CreateDirectory(smFolder);
                CreateLnk(Path.Combine(smFolder, "StreamRix.lnk"), exePath, exeDir);
            }
            catch {}
        }

        private static void CreateLnk(string lnkPath, string targetPath, string workDir)
        {
            try
            {
                Type shellType = Type.GetTypeFromProgID("WScript.Shell");
                if (shellType != null)
                {
                    dynamic shell = Activator.CreateInstance(shellType);
                    dynamic shortcut = shell.CreateShortcut(lnkPath);
                    shortcut.TargetPath = targetPath;
                    shortcut.WorkingDirectory = workDir;
                    shortcut.Description = "StreamRix - Sovereign Cinema & Live TV Player";
                    shortcut.IconLocation = targetPath + ",0";
                    shortcut.Save();
                }
            }
            catch {}
        }

        [DllImport("kernel32.dll", CharSet = CharSet.Auto, SetLastError = true)]
        static extern bool SetDllDirectory(string lpPathName);

        [STAThread]
        static void Main()
        {
            // Set explicit AppUserModelID on process BEFORE any window or COM message pump starts
            try
            {
                SetCurrentProcessExplicitAppUserModelID("StreamRix.Entertainment.Cinema");
            }
            catch {}

            // Extract native WebView2Loader.dll to local appdata bin and register in DLL search path
            try
            {
                string localApp = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                string binDir = Path.Combine(localApp, "StreamRix", "bin");
                Directory.CreateDirectory(binDir);

                string loaderTarget = Path.Combine(binDir, "WebView2Loader.dll");
                if (!File.Exists(loaderTarget))
                {
                    ExtractResource("WebView2Loader.dll", loaderTarget);
                }

                string appDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                string localLoader = Path.Combine(appDir, "WebView2Loader.dll");
                if (!File.Exists(localLoader))
                {
                    try { ExtractResource("WebView2Loader.dll", localLoader); } catch {}
                }

                SetDllDirectory(binDir);
            }
            catch {}

            // Dynamic assembly resolver for embedded Microsoft.Web.WebView2 assemblies
            AppDomain.CurrentDomain.AssemblyResolve += (sender, args) =>
            {
                string resName = new AssemblyName(args.Name).Name + ".dll";
                return LoadEmbeddedAssembly(resName);
            };

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new MainForm());
        }

        private static void ExtractResource(string resourceName, string outputPath)
        {
            try
            {
                var asm = Assembly.GetExecutingAssembly();
                using (var s = asm.GetManifestResourceStream(resourceName))
                {
                    if (s != null)
                    {
                        using (var fs = new FileStream(outputPath, FileMode.Create, FileAccess.Write))
                        {
                            s.CopyTo(fs);
                        }
                    }
                }
            }
            catch {}
        }

        private static Assembly LoadEmbeddedAssembly(string resourceName)
        {
            try
            {
                var asm = Assembly.GetExecutingAssembly();
                using (var s = asm.GetManifestResourceStream(resourceName))
                {
                    if (s == null) return null;
                    byte[] data = new byte[s.Length];
                    s.Read(data, 0, data.Length);
                    return Assembly.Load(data);
                }
            }
            catch
            {
                return null;
            }
        }
    }
}
'''
    cs_file = os.path.join(BUILD_DIR, "Program.cs")
    with open(cs_file, "w", encoding="utf-8") as f:
        f.write(cs_content)
    return cs_file

def build():
    prepare_dirs()
    core_dll, winforms_dll, loader_dll = ensure_webview2_dependencies()
    cs_file = write_csharp_source()

    output_exe = os.path.join(DIST_DIR, "StreamRix.exe")
    website_exe = os.path.join(DOWNLOAD_DIR, "StreamRix.exe")

    refs = [
        f'/r:{core_dll}',
        f'/r:{winforms_dll}',
        '/r:System.dll',
        '/r:System.Drawing.dll',
        '/r:System.Windows.Forms.dll',
        '/r:System.Core.dll',
        '/r:Microsoft.CSharp.dll'
    ]

    res_args = [
        f'/res:{core_dll},Microsoft.Web.WebView2.Core.dll',
        f'/res:{winforms_dll},Microsoft.Web.WebView2.WinForms.dll',
        f'/res:{loader_dll},WebView2Loader.dll'
    ]

    # Embed branding suite to give the executable the authentic ~4.5 MB weight
    splash_4k = os.path.join(ASSETS_DIR, "branding", "splash_4k.png")
    splash_1080p = os.path.join(ASSETS_DIR, "branding", "splash_1080p.png")
    banner_img = os.path.join(PROJECT_ROOT, "STREAMRIX-LOGO.png")

    if os.path.exists(splash_4k):
        res_args.append(f'/res:{splash_4k},Splash4kPayload')
    if os.path.exists(splash_1080p):
        res_args.append(f'/res:{splash_1080p},Splash1080pPayload')
    if os.path.exists(banner_img):
        res_args.append(f'/res:{banner_img},BannerPayload')

    images_dir = os.path.join(ASSETS_DIR, "images")
    if os.path.exists(images_dir):
        for idx, f in enumerate(os.listdir(images_dir)):
            if f.endswith((".png", ".jpg", ".webp")):
                res_path = os.path.join(images_dir, f)
                res_args.append(f'/res:{res_path},AssetImage_{idx}')

    cmd = [CSC, '/target:winexe', '/optimize+', f'/win32icon:{ICON_PATH}', f'/out:{output_exe}'] + refs + res_args + [cs_file]
    print("[>] Compiling native Windows desktop executable (StreamRix.exe)...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("[!] Compilation error:")
        print(res.stderr)
        print(res.stdout)
        raise RuntimeError("Failed to compile StreamRix.exe")

    shutil.copy2(output_exe, website_exe)
    size_mb = os.path.getsize(output_exe) / (1024 * 1024)
    print(f"\n=================================================================")
    print(f"🎉 NATIVE WINDOWS DESKTOP EXECUTABLE SUCCESSFULLY COMPILED!")
    print(f"File: {output_exe}")
    print(f"Website Download File: {website_exe}")
    print(f"Size: {size_mb:.2f} MB")
    print(f"Features: Native Taskbar Icon, Pinned StreamRix Identity, Auto Desktop Shortcut, Embedded WebView2 Engine")
    print(f"=================================================================\n")
    return output_exe

if __name__ == "__main__":
    build()
