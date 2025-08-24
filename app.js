// Firebase Configuration (apna config daalna yahan)
const firebaseConfig = {
    apiKey: "YOUR_API_KEY",
    authDomain: "parentguard-app.firebaseapp.com",
    projectId: "parentguard-app",
    storageBucket: "parentguard-app.appspot.com",
    messagingSenderId: "123456789",
    appId: "YOUR_APP_ID"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();
const db = firebase.firestore();

// Login Function
document.getElementById('loginForm')?.addEventListener('submit', (e) => {
    e.preventDefault();
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    auth.signInWithEmailAndPassword(email, password)
        .then((userCredential) => {
            window.location.href = 'dashboard.html';
        })
        .catch((error) => {
            alert('Login failed: ' + error.message);
        });
});

// Logout Function
document.getElementById('logoutBtn')?.addEventListener('click', () => {
    auth.signOut().then(() => {
        window.location.href = 'index.html';
    });
});