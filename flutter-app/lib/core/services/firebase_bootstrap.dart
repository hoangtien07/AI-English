/// Executes Firebase initialization only when its caller has passed every
/// configuration gate. A failure stays fail-closed so later startup work does
/// not use Firebase services against an uninitialized default app.
class FirebaseBootstrap {
  const FirebaseBootstrap._();

  static Future<bool> initialize({
    required bool enabled,
    required Future<void> Function() initializeApp,
  }) async {
    if (!enabled) return false;

    try {
      await initializeApp();
      return true;
    } catch (_) {
      return false;
    }
  }
}
