// Firebase client identifiers are public configuration, not server secrets.
// This project intentionally supports Firebase on Web only.

import 'package:firebase_core/firebase_core.dart'
    show Firebase, FirebaseOptions;
import 'package:flutter/foundation.dart' show kIsWeb;

class DefaultFirebaseOptions {
  /// Facebook is intentionally unavailable on Web; Google is the sole owned
  /// Firebase Web identity provider.
  static const bool isFacebookWebSignInEnabled = false;

  static bool get isWebConfigured =>
      _isConfiguredValue(web.apiKey) &&
      _isConfiguredValue(web.appId) &&
      _isConfiguredValue(web.messagingSenderId) &&
      _isConfiguredValue(web.projectId) &&
      _isConfiguredValue(web.authDomain);

  /// True only when the running platform is Web and its public config is whole.
  static bool get isConfigured => kIsWeb && isWebConfigured;

  /// True only after the configured Firebase app has initialized successfully.
  static bool get isReady => isConfigured && Firebase.apps.isNotEmpty;

  static bool _isConfiguredValue(String? value) =>
      value != null && value.trim().isNotEmpty && !value.startsWith('YOUR_');

  static FirebaseOptions get currentPlatform {
    if (kIsWeb) {
      return web;
    }
    throw UnsupportedError(
      'Firebase is configured for Web only. Do not enable it on this platform.',
    );
  }

  static const FirebaseOptions web = FirebaseOptions(
    apiKey: 'AIzaSyAjV0jileGzbPcHgKZDi4C94N9Ia7GTags',
    appId: '1:403021618812:web:4bd9f953967280ddc4b3f9',
    messagingSenderId: '403021618812',
    projectId: 'english-5d522',
    authDomain: 'english-5d522.firebaseapp.com',
    storageBucket: 'english-5d522.firebasestorage.app',
    measurementId: 'G-QQ057LF052',
  );
}
