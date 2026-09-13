importScripts("https://www.gstatic.com/firebasejs/10.7.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.7.0/firebase-messaging-compat.js");

const firebaseConfig = {
  apiKey: "YOUR_WEB_API_KEY",
  authDomain: "YOUR_AUTH_DOMAIN",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_STORAGE_BUCKET",
  messagingSenderId: "YOUR_MESSAGING_SENDER_ID",
  appId: "YOUR_WEB_APP_ID",
  measurementId: "YOUR_MEASUREMENT_ID",
};

// Service workers cannot read Flutter's bundled dotenv assets. Keep this
// separate flag true only when it matches the Flutter Web configuration and
// FIREBASE_ENABLED=true in the bundled environment assets.
const firebaseEnabled = true;

// Keep messaging inert unless this worker is deliberately enabled and retains
// the complete generated identifiers from the owned Firebase Web app.
if (
  firebaseEnabled &&
  !firebaseConfig.apiKey.startsWith("YOUR_") &&
  !firebaseConfig.appId.startsWith("YOUR_") &&
  !firebaseConfig.messagingSenderId.startsWith("YOUR_")
) {
  firebase.initializeApp(firebaseConfig);
  const messaging = firebase.messaging();

  messaging.onBackgroundMessage((payload) => {
    const { title, body, icon } = payload.notification ?? {};
    self.registration.showNotification(title ?? "LexiLingo", {
      body: body ?? "",
      icon: icon ?? "/icons/Icon-192.png",
    });
  });
}
