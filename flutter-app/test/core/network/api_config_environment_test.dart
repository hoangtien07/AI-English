import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:lexilingo_app/core/network/api_config.dart';

void main() {
  tearDown(() => dotenv.loadFromString(envString: 'ENVIRONMENT=development'));

  test('debug configuration uses the explicit loopback development endpoints', () {
    dotenv.loadFromString(
      envString: '''
ENVIRONMENT=development
DEBUG_MODE=true
API_BASE_URL=http://127.0.0.1:8000/api/v1
AI_SERVICE_URL=http://127.0.0.1:8001/api/v1
''',
    );

    expect(ApiConfig.baseUrl, 'http://127.0.0.1:8000/api/v1');
    expect(ApiConfig.aiServiceUrl, 'http://127.0.0.1:8001/api/v1');
  });

  test('release-equivalent configuration fails closed without owned endpoints', () {
    dotenv.loadFromString(
      envString: 'ENVIRONMENT=production\nDEBUG_MODE=false',
    );

    expect(() => ApiConfig.baseUrl, throwsStateError);
    expect(() => ApiConfig.aiServiceUrl, throwsStateError);
    expect(ApiConfig.fallbackBaseUrl, isEmpty);
    expect(ApiConfig.fallbackAiServiceUrl, isEmpty);
  });

  test('release-equivalent configuration rejects loopback endpoints', () {
    dotenv.loadFromString(
      envString: '''
ENVIRONMENT=production
DEBUG_MODE=false
API_BASE_URL=http://127.0.0.1:8000/api/v1
AI_SERVICE_URL=http://127.0.0.1:8001/api/v1
''',
    );

    expect(() => ApiConfig.baseUrl, throwsStateError);
    expect(() => ApiConfig.aiServiceUrl, throwsStateError);
  });
}
