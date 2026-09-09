# Firebase Web local setup

Firebase is deliberately **Web-only** in this Flutter project. The repository
keeps Firebase inactive unless both the complete public Web SDK configuration
and `FIREBASE_ENABLED=true` are present. No server credentials,
service accounts, or Google OAuth client secrets belong in this application.

## Current owned app

The project is `english-5d522`. Firebase CLI discovery on 2026-09-09 found no
Web apps, so this repository registered the sole owned Web app: **AI English
Web** (`1:403021618812:web:4bd9f953967280ddc4b3f9`). Its public SDK
configuration is installed in the Web-only Flutter and service-worker paths.

## One-time app registration

Authenticate using an account with access to the owned project, then inspect
the existing Web apps before changing anything:

```powershell
npm exec --yes --package=firebase-tools -- firebase login
npm exec --yes --package=firebase-tools -- firebase apps:list WEB --project english-5d522
```

If the list contains the owned **AI English Web** app, use that app. If it does
not, create exactly one app with this deterministic display name (do not create
Android or iOS apps, and do not modify other apps):

```powershell
npm exec --yes --package=firebase-tools -- firebase apps:create WEB "AI English Web" --project english-5d522
```

Fetch that app's public SDK object, replacing `<WEB_APP_ID>` with the returned
app id:

```powershell
npm exec --yes --package=firebase-tools -- firebase apps:sdkconfig WEB <WEB_APP_ID> --project english-5d522
```

Copy only the generated public `apiKey`, `appId`, `messagingSenderId`,
`projectId`, `authDomain`, `storageBucket`, and optional `measurementId` into
both `lib/firebase_options.dart` and `web/firebase-messaging-sw.js`. Replace
the Web id in `firebase.json`, set `FIREBASE_ENABLED=true` in both bundled
`assets/env/*_config` files, and set the service worker's local
`firebaseEnabled` constant to `true`; leave every non-Web Firebase setting
absent. The Firebase Web config object is public client configuration; an OAuth
client secret or service-account JSON must never be copied here.

`flutterfire configure --platforms=web` can generate
`lib/firebase_options.dart` after the Web app is registered. Review the
generated file before accepting it: it must contain only the Web platform and
must preserve the fail-closed guard in this repository.

## Required Firebase Console actions for local Google sign-in

1. In **Firebase console → Authentication → Sign-in method**, enable the
   Google provider and select the support email. Leave the Facebook provider
   disabled: this app hard-disables Facebook sign-in on Web. Do not paste the
   Google OAuth client secret into Flutter or any Flutter asset.
2. In **Authentication → Settings → Authorized domains**, add `localhost` and
   `127.0.0.1` for local development. These entries are hostnames, so they do
   not include a scheme or port. Firebase projects created after April 2025 do
   not automatically trust `localhost`.
3. Use one fixed local origin while testing, for example:

   ```powershell
   flutter run -d chrome --web-port 5173
   ```

   This serves the app at `http://localhost:5173` (or
   `http://127.0.0.1:5173` if opened that way). Use only the hostnames added in
   the preceding step.
4. Keep the generated `authDomain` as
   `english-5d522.firebaseapp.com` unless a custom Auth domain is intentionally
   configured. With the default domain, Firebase uses the redirect handler
   `https://english-5d522.firebaseapp.com/__/auth/handler`; do not substitute a
   localhost `/__/auth/handler` URL. The default Firebase domain is normally
   authorized for the Firebase-managed Google provider. If the project uses a
   manually managed/custom OAuth client and it reports `origin_mismatch`, add
   the exact local origin in use (`http://localhost:5173` and/or
   `http://127.0.0.1:5173`) to that client's **Authorized JavaScript origins**,
   and add the generated Auth redirect handler above to its **Authorized
   redirect URIs**.

## Verification

Run the focused configuration test first:

```powershell
flutter test test/core/services/firebase_options_test.dart
```

The options test verifies the public identifiers, Facebook Web gate, and
Web-only platform gate. Also run the bootstrap and service-worker consistency
tests to prove a closed configuration gate and an initialization failure remain
fail-closed:

```powershell
flutter test test/core/services/firebase_bootstrap_test.dart test/core/services/firebase_web_config_consistency_test.dart
```

Then use `flutter run -d chrome --web-port 5173` to verify initialization and
Google popup/redirect sign-in. Finish with `flutter analyze` and `flutter build
web`; neither command should cause a Firebase project mutation.

References: [Firebase CLI app commands](https://firebase.google.com/docs/cli),
[FlutterFire setup](https://firebase.google.com/docs/flutter/setup), and
[Firebase Auth Google sign-in](https://firebase.google.com/docs/auth/web/google-signin).
