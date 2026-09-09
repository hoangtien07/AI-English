importScripts("https://www.gstatic.com/firebasejs/10.7.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.7.0/firebase-messaging-compat.js");

const firebaseConfig = {
  apiKey: "AIzaSyAjV0jileGzbPcHgKZDi4C94N9Ia7GTags",
  authDomain: "english-5d522.firebaseapp.com",
  projectId: "english-5d522",
  storageBucket: "english-5d522.firebasestorage.app",
  messagingSenderId: "403021618812",
  appId: "1:403021618812:web:4bd9f953967280ddc4b3f9",
  measurementId: "G-QQ057LF052",
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
