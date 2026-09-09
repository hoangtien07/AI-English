import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter_test/flutter_test.dart';
import 'package:lexilingo_app/firebase_options.dart';

void main() {
  test(
    'Web configuration is enabled only when every required value is present',
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

      expect(DefaultFirebaseOptions.isWebConfigured, !hasPlaceholder);
      expect(DefaultFirebaseOptions.isConfigured, kIsWeb);
      expect(DefaultFirebaseOptions.isReady, isFalse);
    },
  );

  test('Firebase client identifiers remain Web configuration fields', () {
    expect(DefaultFirebaseOptions.web.projectId, 'english-5d522');
    expect(
      DefaultFirebaseOptions.web.appId,
      '1:403021618812:web:4bd9f953967280ddc4b3f9',
    );
    expect(DefaultFirebaseOptions.web.projectId, isNotEmpty);
    expect(DefaultFirebaseOptions.web.messagingSenderId, isNotEmpty);
    expect(DefaultFirebaseOptions.web.apiKey, isNotEmpty);
    expect(DefaultFirebaseOptions.web.appId, isNotEmpty);
    expect(DefaultFirebaseOptions.web.measurementId, 'G-QQ057LF052');
    expect(DefaultFirebaseOptions.isFacebookWebSignInEnabled, isFalse);
  });

  test('only exposes a Firebase platform option on Web', () {
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
}
