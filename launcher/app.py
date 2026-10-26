
import os
import traceback

from kivy.app import App
from kivy.clock import Clock
from kivy.utils import platform
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView


STORAGE_ROOT = "/storage/emulated/0/kivy"


class KivyLauncherApp(App):

    def build(self):
        self.title = "Kivy Launcher"

        self.root_layout = BoxLayout(
            orientation="vertical",
            padding=10,
            spacing=8,
        )

        self.status = Label(
            text="Checking storage access...",
            size_hint_y=None,
            height=45,
        )
        self.root_layout.add_widget(self.status)

        controls = BoxLayout(
            size_hint_y=None,
            height=48,
            spacing=8,
        )

        refresh_button = Button(text="Refresh")
        refresh_button.bind(on_release=self.refresh_entries)
        controls.add_widget(refresh_button)

        permission_button = Button(text="Storage Permission")
        permission_button.bind(
            on_release=self.open_storage_settings
        )
        controls.add_widget(permission_button)

        self.root_layout.add_widget(controls)

        self.scroll = ScrollView()
        self.app_list = BoxLayout(
            orientation="vertical",
            spacing=6,
            size_hint_y=None,
        )
        self.app_list.bind(
            minimum_height=self.app_list.setter("height")
        )
        self.scroll.add_widget(self.app_list)
        self.root_layout.add_widget(self.scroll)

        if platform == "android":
            try:
                from android import activity
                activity.bind(on_resume=self.on_resume)
            except Exception:
                self.log_error("Could not bind Android resume callback")

            Clock.schedule_once(
                lambda dt: self.check_storage_access(
                    open_settings_if_denied=True
                ),
                0.5,
            )
        else:
            self.refresh_entries()

        return self.root_layout

    def check_storage_access(self, open_settings_if_denied=False):
        if platform != "android":
            self.refresh_entries()
            return False

        try:
            from jnius import autoclass

            Environment = autoclass("android.os.Environment")
            granted = Environment.isExternalStorageManager()

            if granted:
                self.status.text = "Storage access granted"
                self.refresh_entries()
                return True

            self.status.text = (
                "Allow all-files access in Android Settings."
            )

            if open_settings_if_denied:
                self.open_storage_settings()

            return False

        except Exception:
            self.status.text = "Could not check storage permission"
            self.log_error(traceback.format_exc())
            return False

    def open_storage_settings(self, *args):
        if platform != "android":
            self.status.text = "Android settings are only available on Android"
            return

        try:
            from jnius import autoclass

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )
            Intent = autoclass("android.content.Intent")
            Settings = autoclass("android.provider.Settings")
            Uri = autoclass("android.net.Uri")

            activity_instance = PythonActivity.mActivity
            package_name = activity_instance.getPackageName()

            intent = Intent(
                Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION
            )
            intent.setData(Uri.parse("package:" + package_name))

            activity_instance.startActivity(intent)

        except Exception:
            self.status.text = (
                "Could not open app-specific settings. "
                "Open All files access manually in Android Settings."
            )
            self.log_error(traceback.format_exc())

    def on_resume(self, *args):
        # Recheck permission when returning from Android Settings.
        Clock.schedule_once(
            lambda dt: self.check_storage_access(
                open_settings_if_denied=False
            ),
            0.5,
        )

    def refresh_entries(self, *args):
        self.app_list.clear_widgets()

        if platform == "android":
            try:
                from jnius import autoclass

                Environment = autoclass("android.os.Environment")

                if not Environment.isExternalStorageManager():
                    self.status.text = (
                        "Storage permission is missing. "
                        "Tap Storage Permission."
                    )
                    return
            except Exception:
                self.status.text = "Unable to verify storage access"
                self.log_error(traceback.format_exc())
                return

        if not os.path.isdir(STORAGE_ROOT):
            self.status.text = (
                f"Folder not found: {STORAGE_ROOT}"
            )
            return

        try:
            entries = sorted(os.listdir(STORAGE_ROOT))
        except OSError as exc:
            self.status.text = f"Cannot read storage: {exc}"
            self.log_error(traceback.format_exc())
            return

        found = 0

        for entry in entries:
            app_dir = os.path.join(STORAGE_ROOT, entry)

            if not os.path.isdir(app_dir):
                continue

            main_file = os.path.join(app_dir, "main.py")
            metadata_file = os.path.join(app_dir, "android.txt")

            if not (
                os.path.isfile(main_file)
                and os.path.isfile(metadata_file)
            ):
                continue

            try:
                with open(
                    metadata_file,
                    "r",
                    encoding="utf-8",
                    errors="replace",
                ) as file:
                    metadata = file.read().strip()

                display_name = metadata or entry
            except OSError:
                display_name = entry

            button = Button(
                text=f"{display_name}\n{entry}",
                size_hint_y=None,
                height=65,
            )
            button.bind(
                on_release=lambda instance, path=app_dir:
                    self.show_app_info(path)
            )
            self.app_list.add_widget(button)
            found += 1

        self.status.text = (
            f"Found {found} app(s) in {STORAGE_ROOT}"
        )

    def show_app_info(self, app_dir):
        # Discovery works independently of app execution.
        # Do not execute arbitrary main.py files in the
        # launcher process without a compatible app interface.
        self.status.text = (
            f"Selected: {os.path.basename(app_dir)}. "
            "App execution is not implemented in this example."
        )

    def log_error(self, message):
        print("[KivyLauncher]", message)


if __name__ == "__main__":
    KivyLauncherApp().run()
        
