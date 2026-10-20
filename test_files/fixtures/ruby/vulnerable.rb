# Vulnerable Ruby test fixture for static analysis verification (RuboCop)

class ReportService
  # Hardcoded sensitive API key (RuboCop Security/HardcodedSecret, CWE-798)
  API_KEY = "RB_SEC_PROD_998877665544332211"

  def generate_report(user_id)
    puts "Generating report for #{user_id} using key #{API_KEY}"
  end
end
