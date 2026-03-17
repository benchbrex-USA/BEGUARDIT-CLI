# Job: generate_html_report
# Input: {session_id, tenant_id, job_id}
# Output: HTML file written to REPORT_STORAGE_PATH; report_jobs row updated
# Timeout: 5min, Retries: 3
# Idempotent: checks for existing completed output before processing
