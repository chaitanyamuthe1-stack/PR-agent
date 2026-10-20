// Clean JavaScript test fixture (Phase 6 verification)

function authenticateUser(token, role) {
    // Strict equality (eqeqeq safe)
    if (role === "admin") {
        const secret = process.env.JWT_SECRET || "fallback_vault_token";
        return token === secret;
    }
    return false;
}

module.exports = { authenticateUser };
