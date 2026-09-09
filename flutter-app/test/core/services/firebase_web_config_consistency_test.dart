import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:lexilingo_app/firebase_options.dart';

void main() {
  test('messaging service worker matches the owned Firebase Web app', () {
    final serviceWorker = File('web/firebase-messaging-sw.js')
        .readAsStringSync();
    final web = DefaultFirebaseOptions.web;

    expect(serviceWorker, contains('apiKey: "${web.apiKey}"'));
    expect(serviceWorker, contains('appId: "${web.appId}"'));
    expect(
      serviceWorker,
      contains('messagingSenderId: "${web.messagingSenderId}"'),
    );
    expect(serviceWorker, contains('projectId: "${web.projectId}"'));
    expect(serviceWorker, contains('authDomain: "${web.authDomain}"'));
    expect(serviceWorker, contains('storageBucket: "${web.storageBucket}"'));
    expect(serviceWorker, contains('measurementId: "${web.measurementId}"'));
    expect(serviceWorker, contains('const firebaseEnabled = true;'));
  });
}
