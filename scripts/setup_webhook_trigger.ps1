# setup_webhook_trigger.ps1
# Run this script to verify and fix the Jenkins webhook trigger configuration.
# Run from inside the ai-sdlc-poc directory.

param(
    [string]$GiteaUrl = "http://localhost:3000",
    [string]$JenkinsUrl = "http://localhost:8080",
    [string]$GiteaUser = "gitadmin",
    [string]$GiteaPass = "Admin@1234!",
    [string]$WebhookToken = "jenkins-webhook-secret",
    [string]$OrgRepo = "ai-sdlc-poc/app-repo"
)

Write-Host ""
Write-Host "======================================================" -ForegroundColor Cyan
Write-Host "  Webhook Trigger Setup Verification" -ForegroundColor Cyan
Write-Host "======================================================" -ForegroundColor Cyan

$WebhookUrl = "http://jenkins-server:8080/generic-webhook-trigger/invoke?token=$WebhookToken"

Write-Host ""
Write-Host "STEP 1 - Verify Jenkins is reachable" -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest -Uri "$JenkinsUrl" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
    Write-Host "  [OK] Jenkins responding at $JenkinsUrl" -ForegroundColor Green
} catch {
    Write-Host "  [FAIL] Jenkins not reachable at $JenkinsUrl" -ForegroundColor Red
    Write-Host "  Run: docker compose up -d jenkins-server" -ForegroundColor Gray
    exit 1
}

Write-Host ""
Write-Host "STEP 2 - Check Generic Webhook Trigger plugin" -ForegroundColor Yellow
Write-Host "  Open: $JenkinsUrl/pluginManager/installed" -ForegroundColor Gray
Write-Host "  Look for: Generic Webhook Trigger" -ForegroundColor Gray
Write-Host "  If missing: $JenkinsUrl/pluginManager/available - search and install it" -ForegroundColor Gray
Write-Host ""
Write-Host "  The plugin endpoint will be:" -ForegroundColor Gray
Write-Host "  $JenkinsUrl/generic-webhook-trigger/invoke?token=$WebhookToken" -ForegroundColor White

Write-Host ""
Write-Host "STEP 3 - Configure Gitea Webhook" -ForegroundColor Yellow
Write-Host "  Open: $GiteaUrl/$OrgRepo/settings/hooks" -ForegroundColor Gray
Write-Host ""
Write-Host "  If no webhook exists, click 'Add Webhook' -> Gitea and set:" -ForegroundColor Gray
Write-Host "    Target URL  : $WebhookUrl" -ForegroundColor White
Write-Host "    HTTP Method : POST" -ForegroundColor White
Write-Host "    Content Type: application/json" -ForegroundColor White
Write-Host "    Secret Token: (leave blank)" -ForegroundColor White
Write-Host "    Trigger On  : Push Events (check this)" -ForegroundColor White
Write-Host "    Active      : checked" -ForegroundColor White
Write-Host ""
Write-Host "  If a webhook exists, edit it and update the Target URL to:" -ForegroundColor Gray
Write-Host "  $WebhookUrl" -ForegroundColor White

Write-Host ""
Write-Host "STEP 4 - Configure Jenkins job trigger" -ForegroundColor Yellow
Write-Host "  Open: $JenkinsUrl -> your pipeline job -> Configure" -ForegroundColor Gray
Write-Host "  Scroll to 'Build Triggers'" -ForegroundColor Gray
Write-Host "  Check 'Generic Webhook Trigger'" -ForegroundColor Gray
Write-Host "  Set Token: $WebhookToken" -ForegroundColor White
Write-Host "  Leave all other fields empty" -ForegroundColor Gray
Write-Host "  Click Save" -ForegroundColor Gray

Write-Host ""
Write-Host "STEP 5 - Disable CSRF (required for webhooks in PoC)" -ForegroundColor Yellow
Write-Host "  $JenkinsUrl/configureSecurity" -ForegroundColor Gray
Write-Host "  Uncheck: 'Prevent Cross Site Request Forgery exploits'" -ForegroundColor Gray
Write-Host "  Save" -ForegroundColor Gray

Write-Host ""
Write-Host "STEP 6 - Test the webhook" -ForegroundColor Yellow
Write-Host "  In Gitea: $GiteaUrl/$OrgRepo/settings/hooks" -ForegroundColor Gray
Write-Host "  Click your webhook -> scroll down -> 'Test Delivery'" -ForegroundColor Gray
Write-Host "  Expect HTTP 200 response" -ForegroundColor Gray
Write-Host "  Check Jenkins - a new build should have started" -ForegroundColor Gray

Write-Host ""
Write-Host "STEP 7 - Verify end-to-end from workspace-dev1" -ForegroundColor Yellow
Write-Host "  cd ..\workspace-dev1" -ForegroundColor Gray
Write-Host "  echo '# trigger test' >> app\src\main.py" -ForegroundColor Gray
Write-Host "  git add ." -ForegroundColor Gray
Write-Host "  git commit -m 'feat: test webhook auto-trigger'" -ForegroundColor Gray
Write-Host "  git push origin feat/dev1-auth-module" -ForegroundColor Gray
Write-Host "  -> Watch Jenkins: build should start in 2-3 seconds" -ForegroundColor Gray

Write-Host ""
Write-Host "======================================================" -ForegroundColor Green
Write-Host "  Webhook URL to use in Gitea:" -ForegroundColor Green
Write-Host "  $WebhookUrl" -ForegroundColor White
Write-Host "======================================================" -ForegroundColor Green
