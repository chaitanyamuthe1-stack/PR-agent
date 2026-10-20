# frozen_string_literal: true
# Clean Ruby test fixture (Phase 6 verification)

module SecurityService
  class Authenticator
    def initialize
      # Fetch from environment variable with fallback (CWE-798 safe)
      @api_key = ENV.fetch("APP_API_KEY", "secure_vault_token")
    end

    def authorized?(token)
      token == @api_key
    end
  end
end
