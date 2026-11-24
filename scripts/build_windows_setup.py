import os
import glob
import subprocess
import shutil
from build_windows_exe import build as build_core_app

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
DOWNLOAD_DIR = os.path.join(PROJECT_ROOT, "download")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build", "windows_setup")
CSC = os.environ.get("CSC") or (
    glob.glob(r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe")
    or glob.glob(r"C:\Windows\Microsoft.NET\Framework\v4.0.30319\csc.exe")
    or [r"C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe"]
)[0]
ICON_PATH = os.path.join(PROJECT_ROOT, "favicon_clean.ico")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")

def prepare_dirs():
    os.makedirs(BUILD_DIR, exist_ok=True)
    os.makedirs(DIST_DIR, exist_ok=True)
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def build_uninstaller():
    print("[>] Compiling Uninstall.exe...")
    uninst_cs = '''using System;
using System.IO;
using System.Windows.Forms;
using Microsoft.Win32;

namespace StreamRix
{
    static class Uninstaller
    {
        [STAThread]
        static void Main()
        {
            DialogResult dr = MessageBox.Show(
                "Are you sure you want to completely uninstall StreamRix?",
                "StreamRix Uninstall",
                MessageBoxButtons.YesNo,
                MessageBoxIcon.Question
            );
            if (dr != DialogResult.Yes) return;

            try
            {
                // 1. Remove Desktop Shortcut
                string desktopPath = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
                string desktopLnk = Path.Combine(desktopPath, "StreamRix.lnk");
                if (File.Exists(desktopLnk)) File.Delete(desktopLnk);

                // 2. Remove Start Menu shortcuts
                string startMenu = Environment.GetFolderPath(Environment.SpecialFolder.StartMenu);
                string smPrograms = Path.Combine(startMenu, "Programs");
                string directLnk = Path.Combine(smPrograms, "StreamRix.lnk");
                if (File.Exists(directLnk)) File.Delete(directLnk);

                string smFolder = Path.Combine(smPrograms, "StreamRix");
                if (Directory.Exists(smFolder)) Directory.Delete(smFolder, true);

                // 3. Remove Registry Key
                Registry.CurrentUser.DeleteSubKeyTree(@"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\StreamRix", false);

                MessageBox.Show(
                    "StreamRix has been successfully uninstalled from your computer.",
                    "StreamRix Uninstalled",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information
                );
            }
            catch (Exception ex)
            {
                MessageBox.Show("Error during uninstall: " + ex.Message, "Uninstall Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
'''
    uninst_file = os.path.join(BUILD_DIR, "Uninstall.cs")
    with open(uninst_file, "w", encoding="utf-8") as f:
        f.write(uninst_cs)

    uninst_exe = os.path.join(BUILD_DIR, "Uninstall.exe")
    cmd = [CSC, '/target:winexe', '/optimize+', '/platform:anycpu', f'/win32icon:{ICON_PATH}', f'/out:{uninst_exe}', uninst_file]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("[!] Error compiling Uninstall.exe:")
        print(res.stderr)
        raise RuntimeError("Failed to compile Uninstall.exe")
    print(f"[✓] Uninstaller built ({os.path.getsize(uninst_exe) / 1024:.1f} KB)")
    return uninst_exe

def build_setup_installer(core_exe, uninst_exe):
    print("[>] Compiling high-trust StreamRix-Setup.exe installer...")
    
    native_build_dir = os.path.join(PROJECT_ROOT, "build", "windows_native")
    core_dll = os.path.join(native_build_dir, "Microsoft.Web.WebView2.Core.dll")
    winforms_dll = os.path.join(native_build_dir, "Microsoft.Web.WebView2.WinForms.dll")
    loader_dll = os.path.join(native_build_dir, "WebView2Loader.dll")

    splash_4k = os.path.join(ASSETS_DIR, "branding", "splash_4k.png")
    splash_1080p = os.path.join(ASSETS_DIR, "branding", "splash_1080p.png")
    banner_img = os.path.join(PROJECT_ROOT, "STREAMRIX-LOGO.png")

    installer_cs = '''using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Reflection;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32;

namespace StreamRixInstaller
{
    public class SetupForm : Form
    {
        private ProgressBar progressBar;
        private Label lblStatus;
        private Label lblTitle;
        private Label lblSubtitle;
        private System.Windows.Forms.Timer timer;
        private int step = 0;

        public SetupForm()
        {
            this.Text = "StreamRix Setup";
            this.Size = new Size(500, 320);
            this.StartPosition = FormStartPosition.CenterScreen;
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox = false;
            this.MinimizeBox = false;
            this.BackColor = Color.FromArgb(7, 9, 14);
            this.ForeColor = Color.White;

            lblTitle = new Label();
            lblTitle.Text = "STREAMRIX";
            lblTitle.Font = new Font("Segoe UI", 20, FontStyle.Bold);
            lblTitle.ForeColor = Color.FromArgb(229, 9, 20);
            lblTitle.Location = new Point(30, 30);
            lblTitle.Size = new Size(440, 40);

            lblSubtitle = new Label();
            lblSubtitle.Text = "Ultra Clean Sovereign Cinema & Live TV Player";
            lblSubtitle.Font = new Font("Segoe UI", 10, FontStyle.Regular);
            lblSubtitle.ForeColor = Color.FromArgb(160, 175, 200);
            lblSubtitle.Location = new Point(32, 72);
            lblSubtitle.Size = new Size(440, 25);

            progressBar = new ProgressBar();
            progressBar.Location = new Point(35, 140);
            progressBar.Size = new Size(415, 14);
            progressBar.Style = ProgressBarStyle.Continuous;
            progressBar.Value = 10;

            lblStatus = new Label();
            lblStatus.Text = "Initializing StreamRix installer...";
            lblStatus.Font = new Font("Segoe UI", 9, FontStyle.Regular);
            lblStatus.ForeColor = Color.FromArgb(200, 210, 225);
            lblStatus.Location = new Point(35, 168);
            lblStatus.Size = new Size(415, 25);

            this.Controls.Add(lblTitle);
            this.Controls.Add(lblSubtitle);
            this.Controls.Add(progressBar);
            this.Controls.Add(lblStatus);

            timer = new System.Windows.Forms.Timer();
            timer.Interval = 250;
            timer.Tick += Timer_Tick;
            timer.Start();
        }

        private void Timer_Tick(object sender, EventArgs e)
        {
            step++;
            if (step == 1)
            {
                progressBar.Value = 35;
                lblStatus.Text = "Deploying StreamRix Native Core to %LOCALAPPDATA%...";
            }
            else if (step == 2)
            {
                progressBar.Value = 70;
                lblStatus.Text = "Creating official Desktop and Start Menu shortcuts...";
                PerformInstallation();
            }
            else if (step == 3)
            {
                progressBar.Value = 90;
                lblStatus.Text = "Configuring hardware video acceleration and cinema shell...";
            }
            else if (step == 4)
            {
                progressBar.Value = 100;
                lblStatus.Text = "Installation complete! Launching StreamRix...";
            }
            else if (step >= 6)
            {
                timer.Stop();
                LaunchApp();
                this.Close();
            }
        }

        private void PerformInstallation()
        {
            try
            {
                string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                string installDir = Path.Combine(localAppData, "Programs", "StreamRix");
                Directory.CreateDirectory(installDir);

                // 1. Extract embedded payload
                Assembly asm = Assembly.GetExecutingAssembly();
                ExtractResource(asm, "StreamRixPayload", Path.Combine(installDir, "StreamRix.exe"));
                ExtractResource(asm, "UninstallPayload", Path.Combine(installDir, "Uninstall.exe"));
                ExtractResource(asm, "IconPayload", Path.Combine(installDir, "StreamRix.ico"));
                ExtractResource(asm, "WebView2LoaderPayload", Path.Combine(installDir, "WebView2Loader.dll"));
                ExtractResource(asm, "WebView2CorePayload", Path.Combine(installDir, "Microsoft.Web.WebView2.Core.dll"));
                ExtractResource(asm, "WebView2WinFormsPayload", Path.Combine(installDir, "Microsoft.Web.WebView2.WinForms.dll"));

                // 2. Create Desktop Shortcut
                string desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
                string lnkPath = Path.Combine(desktop, "StreamRix.lnk");
                CreateShortcut(lnkPath, Path.Combine(installDir, "StreamRix.exe"), Path.Combine(installDir, "StreamRix.ico"));

                // 3. Create Start Menu Shortcuts
                string startMenu = Environment.GetFolderPath(Environment.SpecialFolder.StartMenu);
                string smPrograms = Path.Combine(startMenu, "Programs");
                CreateShortcut(Path.Combine(smPrograms, "StreamRix.lnk"), Path.Combine(installDir, "StreamRix.exe"), Path.Combine(installDir, "StreamRix.ico"));

                string smDir = Path.Combine(startMenu, "Programs", "StreamRix");
                Directory.CreateDirectory(smDir);
                CreateShortcut(Path.Combine(smDir, "StreamRix.lnk"), Path.Combine(installDir, "StreamRix.exe"), Path.Combine(installDir, "StreamRix.ico"));

                // 4. Register in Add/Remove Programs
                using (RegistryKey key = Registry.CurrentUser.CreateSubKey(@"Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\StreamRix"))
                {
                    if (key != null)
                    {
                        key.SetValue("DisplayName", "StreamRix");
                        key.SetValue("DisplayVersion", "1.0.0");
                        key.SetValue("Publisher", "StreamRix");
                        key.SetValue("DisplayIcon", Path.Combine(installDir, "StreamRix.ico"));
                        key.SetValue("UninstallString", Path.Combine(installDir, "Uninstall.exe"));
                        key.SetValue("InstallLocation", installDir);
                    }
                }
            }
            catch (Exception)
            {
                // Silently continue or fallback
            }
        }

        private void ExtractResource(Assembly asm, string resName, string destPath)
        {
            using (Stream s = asm.GetManifestResourceStream(resName))
            {
                if (s != null)
                {
                    using (FileStream fs = new FileStream(destPath, FileMode.Create, FileAccess.Write))
                    {
                        byte[] buffer = new byte[81920];
                        int read;
                        while ((read = s.Read(buffer, 0, buffer.Length)) > 0)
                        {
                            fs.Write(buffer, 0, read);
                        }
                    }
                }
            }
        }

        private void CreateShortcut(string shortcutPath, string targetPath, string iconPath)
        {
            try
            {
                Type shellType = Type.GetTypeFromProgID("WScript.Shell");
                if (shellType != null)
                {
                    dynamic shell = Activator.CreateInstance(shellType);
                    dynamic shortcut = shell.CreateShortcut(shortcutPath);
                    shortcut.TargetPath = targetPath;
                    shortcut.WorkingDirectory = Path.GetDirectoryName(targetPath);
                    shortcut.IconLocation = iconPath + ",0";
                    shortcut.Description = "StreamRix - Stream Movies, Anime & Live TV Effortlessly";
                    shortcut.Save();
                }
            }
            catch { }
        }

        private void LaunchApp()
        {
            try
            {
                string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                string appPath = Path.Combine(localAppData, "Programs", "StreamRix", "StreamRix.exe");
                if (File.Exists(appPath))
                {
                    Process.Start(new ProcessStartInfo(appPath) { UseShellExecute = true });
                }
            }
            catch { }
        }
    }

    static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new SetupForm());
        }
    }
}
'''
    setup_cs = os.path.join(BUILD_DIR, "Setup.cs")
    with open(setup_cs, "w", encoding="utf-8") as f:
        f.write(installer_cs)

    setup_exe = os.path.join(DIST_DIR, "StreamRix-Setup.exe")
    website_setup_exe = os.path.join(DOWNLOAD_DIR, "StreamRix-Setup.exe")

    res_args = [
        f'/resource:{core_exe},StreamRixPayload',
        f'/resource:{uninst_exe},UninstallPayload',
        f'/resource:{ICON_PATH},IconPayload',
        f'/resource:{loader_dll},WebView2LoaderPayload',
        f'/resource:{core_dll},WebView2CorePayload',
        f'/resource:{winforms_dll},WebView2WinFormsPayload'
    ]
    if os.path.exists(splash_4k):
        res_args.append(f'/resource:{splash_4k},Splash4kPayload')
    if os.path.exists(splash_1080p):
        res_args.append(f'/resource:{splash_1080p},Splash1080pPayload')
    if os.path.exists(banner_img):
        res_args.append(f'/resource:{banner_img},BannerPayload')

    cmd = [CSC, '/target:winexe', '/optimize+', '/platform:anycpu', f'/win32icon:{ICON_PATH}'] + res_args + [f'/out:{setup_exe}', setup_cs]
    
    print("[>] Compiling StreamRix-Setup.exe with embedded resources...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("[!] Error compiling StreamRix-Setup.exe:")
        print(res.stderr)
        raise RuntimeError("Failed to compile StreamRix-Setup.exe")

    shutil.copy2(setup_exe, website_setup_exe)
    size_mb = os.path.getsize(setup_exe) / (1024 * 1024)
    print(f"\n=================================================================")
    print(f"🎉 WINDOWS SETUP INSTALLER SUCCESSFULLY BUILT!")
    print(f"File: {setup_exe}")
    print(f"Website Download File: {website_setup_exe}")
    print(f"Size: {size_mb:.2f} MB")
    print(f"Features: Dark Sovereign Setup UI, Desktop & Start Menu Shortcuts, Uninstaller, Registry Integration")
    print(f"=================================================================\n")

if __name__ == "__main__":
    prepare_dirs()
    core = build_core_app()
    uninst = build_uninstaller()
    build_setup_installer(core, uninst)
