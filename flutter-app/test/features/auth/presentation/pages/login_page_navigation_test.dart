import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lexilingo_app/features/auth/presentation/pages/login_page.dart';
import 'package:lexilingo_app/features/auth/presentation/providers/auth_provider.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:provider/provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'login_page_navigation_test.mocks.dart';

@GenerateNiceMocks([MockSpec<AuthProvider>()])
class _TestAssetLoader extends AssetLoader {
  const _TestAssetLoader();

  @override
  Future<Map<String, dynamic>> load(String path, Locale locale) async => {};
}

Widget _testApp({
  required AuthProvider authProvider,
  required bool embeddedInAuthWrapper,
}) {
  return EasyLocalization(
    supportedLocales: const [Locale('en')],
    path: 'assets/i18n',
    fallbackLocale: const Locale('en'),
    startLocale: const Locale('en'),
    assetLoader: const _TestAssetLoader(),
    child: Builder(
      builder: (context) => ChangeNotifierProvider<AuthProvider>.value(
        value: authProvider,
        child: MaterialApp(
          locale: context.locale,
          supportedLocales: context.supportedLocales,
          localizationsDelegates: context.localizationDelegates,
          initialRoute: '/login',
          routes: {
            '/': (_) => const Scaffold(body: Text('root-auth-wrapper')),
            '/login': (_) =>
                LoginPage(embeddedInAuthWrapper: embeddedInAuthWrapper),
          },
        ),
      ),
    ),
  );
}

void main() {
  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    SharedPreferences.setMockInitialValues({});
    EasyLocalization.logger.enableLevels = [];
    await EasyLocalization.ensureInitialized();
  });

  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  testWidgets('standalone login resets navigation to root after Google auth', (
    tester,
  ) async {
    final authProvider = MockAuthProvider();
    var authenticated = false;
    when(authProvider.isLoading).thenReturn(false);
    when(authProvider.isAuthenticated).thenAnswer((_) => authenticated);
    when(authProvider.signInWithGoogle()).thenAnswer((_) async {
      authenticated = true;
    });

    await tester.pumpWidget(
      _testApp(authProvider: authProvider, embeddedInAuthWrapper: false),
    );
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('Google'));
    await tester.tap(find.text('Google'));
    await tester.pumpAndSettle();

    verify(authProvider.signInWithGoogle()).called(1);
    expect(find.text('root-auth-wrapper'), findsOneWidget);
    expect(find.byType(LoginPage), findsNothing);
  });

  testWidgets('embedded login leaves post-auth transition to AuthWrapper', (
    tester,
  ) async {
    final authProvider = MockAuthProvider();
    var authenticated = false;
    when(authProvider.isLoading).thenReturn(false);
    when(authProvider.isAuthenticated).thenAnswer((_) => authenticated);
    when(authProvider.signInWithGoogle()).thenAnswer((_) async {
      authenticated = true;
    });

    await tester.pumpWidget(
      _testApp(authProvider: authProvider, embeddedInAuthWrapper: true),
    );
    await tester.pumpAndSettle();

    await tester.ensureVisible(find.text('Google'));
    await tester.tap(find.text('Google'));
    await tester.pumpAndSettle();

    verify(authProvider.signInWithGoogle()).called(1);
    expect(find.byType(LoginPage), findsOneWidget);
    expect(find.text('root-auth-wrapper'), findsNothing);
  });
}
