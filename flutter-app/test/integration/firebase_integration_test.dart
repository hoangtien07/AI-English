import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_test/flutter_test.dart';
import 'package:lexilingo_app/firebase_options.dart';

/// Offline integration boundary tests for Firebase's Web-only configuration.
///
/// These tests intentionally never initialize Firebase or contact the owned
/// project. A real browser smoke test is required only after the public Web SDK
/// config is installed and Firebase Authentication is enabled in the console.
void main() {
  group('Firebase Web configuration', () {
    test(
      'ships a known Web project and accurately gates incomplete config',
      () {
        final web = DefaultFirebaseOptions.web;
        final hasPlaceholder =
            [
              web.apiKey,
              web.appId,
              web.messagingSenderId,
              web.projectId,
              web.authDomain,
            ].any(
              (value) =>
                  value == null ||
                  value.trim().isEmpty ||
                  value.startsWith('YOUR_'),
            );

        expect(DefaultFirebaseOptions.web.projectId, 'english-5d522');
        expect(DefaultFirebaseOptions.isWebConfigured, !hasPlaceholder);
        expect(DefaultFirebaseOptions.isConfigured, kIsWeb);
        expect(DefaultFirebaseOptions.isReady, isFalse);
      },
    );

    test('contains only Web client identifiers', () {
      expect(DefaultFirebaseOptions.web.apiKey, isNotEmpty);
      expect(DefaultFirebaseOptions.web.appId, isNotEmpty);
      expect(DefaultFirebaseOptions.web.messagingSenderId, isNotEmpty);
    });

    test('rejects native Firebase initialization for this Web-only app', () {
      if (kIsWeb) {
        expect(
          DefaultFirebaseOptions.currentPlatform,
          same(DefaultFirebaseOptions.web),
        );
      } else {
        expect(
          () => DefaultFirebaseOptions.currentPlatform,
          throwsA(isA<UnsupportedError>()),
        );
      }
    });
  });
}
