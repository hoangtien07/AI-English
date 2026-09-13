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
    // When placeholders are set, isWebConfigured will be false — this is
    // the expected state in CI / clean checkouts without injected secrets.
    final hasPlaceholder = [
      DefaultFirebaseOptions.web.apiKey,
      DefaultFirebaseOptions.web.appId,
      DefaultFirebaseOptions.web.messagingSenderId,
      DefaultFirebaseOptions.web.projectId,
      DefaultFirebaseOptions.web.authDomain,
    ].any((v) => v == null || v.startsWith('YOUR_'));

    expect(DefaultFirebaseOptions.isWebConfigured, !hasPlaceholder);
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
