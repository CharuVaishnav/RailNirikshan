# RailNirikshan mobile app (Flutter)

One app for both inspecting officers and compliance staff. The screens change with the role of the user who logs in.

## First-time setup

This folder has the app code only. Generate the Android/iOS platform folders once:

```bash
cd mobile
flutter create . --org in.railnirikshan --platforms android
flutter pub get
```

Then add these permissions inside `<manifest>` in `android/app/src/main/AndroidManifest.xml`:

```xml
<uses-permission android:name="android.permission.INTERNET"/>
<uses-permission android:name="android.permission.CAMERA"/>
<uses-permission android:name="android.permission.ACCESS_FINE_LOCATION"/>
<uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION"/>
```

During development the backend runs on plain HTTP, so also add
`android:usesCleartextTraffic="true"` to the `<application>` tag (remove it for the pilot, which uses HTTPS).

## Run

1. Start the backend first (see the main README).
2. Start an Android emulator, or connect a phone with USB debugging on.
3. `flutter run`

On the login screen, the server address is `http://10.0.2.2:8000` for the emulator.
On a real phone, use your laptop's Wi-Fi IP address, for example `http://192.168.1.20:8000`
(phone and laptop on the same Wi-Fi, and start the backend with `--host 0.0.0.0`).

Demo users (after running the seed script): `officer`, `staff_elec`, `staff_comm`, … password `demo123`.

## Share the app with test users (free)

No Play Store account is needed. Build the APK once and send the file to test users:

```bash
flutter build apk --release
# file: build/app/outputs/flutter-apk/app-release.apk
```

They install it after allowing "Install unknown apps" for their file manager or browser.

## What is already built

- Login with role-based home screen
- Officer: new inspection with checklist, add observations with photo + GPS, AI department suggestion,
  AI-drafted note, edit and approve
- Staff: list of department tasks, submit fix with after-photo + GPS, see the AI check result

## Still to build (see the build plan)

- Offline mode: save inspections in SQLite (`sqflite` package) and sync when online (week 4)
- Voice notes: record audio and send it for Whisper transcription (week 7)
- Better photo viewer, push notifications for new tasks
