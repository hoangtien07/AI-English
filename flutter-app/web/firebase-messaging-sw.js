importScripts("https://www.gstatic.com/firebasejs/10.7.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/10.7.0/firebase-messaging-compat.js");

const firebaseConfig = {
  apiKey: "YOUR_WEB_API_KEY",
  authDomain: "english-5d522.firebaseapp.com",
  projectId: "english-5d522",
  storageBucket: "english-5d522.firebasestorage.app",
  messagingSenderId: "403021618812",
  appId: "YOUR_WEB_APP_ID",
};

// Service workers cannot read Flutter's bundled dotenv assets. Keep this
// separate flag false until the generated Web config and console setup are
// complete, then change it deliberately alongside FIREBASE_ENABLED=true.
const firebaseEnabled = false;

// Keep messaging inert until the owned Firebase Web app has supplied its two
// generated identifiers. The Flutter development config also disables
// Firebase, so this worker cannot contact the upstream Firebase project.
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
