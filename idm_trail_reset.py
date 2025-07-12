import tkinter as tk
from tkinter import messagebox
import winreg
import os

class IDMResetApp:
    def __init__(self, root):
        self.root = root
        self.root.title("IDM Trial Reset Tool")
        self.root.geometry("400x300")
        self.root.configure(bg='#f0f0f0')

        # Create main frame
        self.main_frame = tk.Frame(root, bg='#f0f0f0')
        self.main_frame.pack(pady=20, padx=20, expand=True)

        # Title Label
        title_label = tk.Label(
            self.main_frame,
            text="IDM Trial Reset Tool",
            font=("Helvetica", 16, "bold"),
            bg='#f0f0f0'
        )
        title_label.pack(pady=10)

        # Description Label
        desc_label = tk.Label(
            self.main_frame,
            text="This tool will reset your IDM trial period.\nMake sure IDM is closed before proceeding.",
            font=("Helvetica", 10),
            bg='#f0f0f0',
            justify='center'
        )
        desc_label.pack(pady=5)

        # Reset Button
        self.reset_button = tk.Button(
            self.main_frame,
            text="Reset IDM Trial",
            command=self.reset_idm,
            font=("Helvetica", 12),
            bg='#4CAF50',
            fg='white',
            width=20,
            height=2,
            cursor='hand2'  # Changes cursor to hand when hovering
        )
        self.reset_button.pack(pady=20)

        # Status Label
        self.status_label = tk.Label(
            self.main_frame,
            text="",
            font=("Helvetica", 10),
            bg='#f0f0f0',
            wraplength=350
        )
        self.status_label.pack(pady=10)

    def delete_registry_key(self, root_key, key_path):
        try:
            winreg.DeleteKey(root_key, key_path)
            return True
        except WindowsError:
            return False

    def reset_idm(self):
        try:
            # Kill IDM process if running
            os.system("taskkill /f /im IDMan.exe >nul 2>&1")

            # CLSID keys to remove
            clsids = [
                "{7B8E9164-324D-4A2E-A46D-0165FB2000EC}",
                "{6DDF00DB-1234-46EC-8356-27E7B2051192}",
                "{D5B91409-A8CA-4973-9A0B-59F713D25671}",
                "{5ED60779-4DE2-4E07-B862-974CA4FF2E9C}",
                "{07999AC3-058B-40BF-984F-69EB1E554CA7}"
            ]

            # Delete CLSID keys from different locations
            root_keys = [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]
            base_paths = ["Software\\Classes\\CLSID\\", "Software\\Classes\\Wow6432Node\\CLSID\\"]

            for clsid in clsids:
                for root_key in root_keys:
                    for base_path in base_paths:
                        full_path = f"{base_path}{clsid}"
                        self.delete_registry_key(root_key, full_path)

            # Reset IDM registration info
            reg_paths = [
                (winreg.HKEY_CURRENT_USER, "Software\\DownloadManager"),
                (winreg.HKEY_LOCAL_MACHINE, "Software\\Internet Download Manager"),
                (winreg.HKEY_LOCAL_MACHINE, "Software\\Wow6432Node\\Internet Download Manager")
            ]

            for root_key, path in reg_paths:
                try:
                    key = winreg.OpenKey(root_key, path, 0, winreg.KEY_ALL_ACCESS)
                    for value in ["FName", "LName", "Email", "Serial"]:
                        try:
                            winreg.DeleteValue(key, value)
                        except WindowsError:
                            continue
                    winreg.CloseKey(key)
                except WindowsError:
                    continue

            self.status_label.config(
                text="✅ IDM Trial has been reset successfully!\nPlease restart your computer.",
                fg="green"
            )
            messagebox.showinfo(
                "Success",
                "IDM Trial has been reset successfully!\nPlease restart your computer to apply changes."
            )

        except Exception as e:
            self.status_label.config(
                text=f"❌ Error: {str(e)}",
                fg="red"
            )
            messagebox.showerror(
                "Error",
                f"An error occurred while resetting IDM trial:\n{str(e)}"
            )

if __name__ == "__main__":
    root = tk.Tk()
    app = IDMResetApp(root)
    root.mainloop()