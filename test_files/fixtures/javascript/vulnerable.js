// Vulnerable JavaScript test fixture for static analysis verification (ESLint)

function verifyAccess(role, providedKey) {
    // Loose equality check (ESLint eqeqeq violation)
    if (role == "superadmin") {
        // Hardcoded secret key (CWE-798, ESLint no-secrets)
        const JWT_SECRET = "AIzaSyD98765432101234567890ABCDEF";
        return providedKey == JWT_SECRET;
    }
    return false;
}

module.exports = { verifyAccess };
