import 'package:flutter_test/flutter_test.dart';
import 'package:lexilingo_app/core/services/firebase_bootstrap.dart';

void main() {
  group('FirebaseBootstrap', () {
    test('does not initialize when its configuration gate is closed', () async {
      var calls = 0;

      final initialized = await FirebaseBootstrap.initialize(
        enabled: false,
        initializeApp: () async => calls++,
      );

      expect(initialized, isFalse);
      expect(calls, 0);
    });

    test('reports successful initialization', () async {
      final initialized = await FirebaseBootstrap.initialize(
        enabled: true,
        initializeApp: () async {},
      );

      expect(initialized, isTrue);
    });

    test('fails closed when Firebase initialization throws', () async {
      final initialized = await FirebaseBootstrap.initialize(
        enabled: true,
        initializeApp: () async => throw StateError('initialization failed'),
      );

      expect(initialized, isFalse);
    });
  });
}
