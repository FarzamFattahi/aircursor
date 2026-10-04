# Updating the original portable desktop app

The supplied AI Cursor directory contains a frozen Python 3.12/PyInstaller application, not its editable Qt source. This update preserves its original interface, camera pipeline, settings, and dependencies, and replaces interaction modules with the maintained repository implementation. The original executable is never modified by the update tool.

Use Python 3.12 from the repository root:

```powershell
python packaging/update_portable.py "C:\path\AirCursor\AirCursor.exe" "C:\path\AirCursor\AirCursor-improved.exe"
```

Keep the generated EXE beside the original `_internal` directory. It is not a standalone one-file application. The updater verifies the original SHA256 and rejects unsupported builds or existing output files. It needs only the Python standard library. The original PyInstaller bootloader and original modules are preserved in the generated binary; original proprietary Qt source is not claimed to have been recovered or published.

The compatibility adapters translate enums for the existing worker, defer button events until pointer positioning, apply Windows' double-click interval, and enlarge the window with remembered geometry. The window extension runs after the original main-window module. User video is not recorded or included in the repository screenshots.

## Local checks

```powershell
AirCursor-improved.exe --aircursor-self-test "C:\temp\runtime.json"
AirCursor-improved.exe --aircursor-native-test "C:\temp\input.json"
```

The first check uses the actual frozen runtime and Qt main window, writes JSON and a screenshot, and does not start hand control or capture a camera preview. The original settings dialog may briefly enumerate available cameras. The second temporarily opens a dedicated foreground window and sends real Windows click/double-click/drag events to it, restores the previous pointer position, and closes. It aborts without clicking if the target cannot receive focus. Parent output folders must already exist. Native test failures are recorded in a sibling `.error.txt` file.

Physical webcam QA is still required: test your camera, lighting, thumb/index release, target selection, double-click rhythm, drag, scroll, tracking loss, and emergency stop. Scripted Windows events validate input delivery, not real landmark recognition.
