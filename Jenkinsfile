pipeline {
    agent any

    environment {
        ANTHROPIC_API_KEY = credentials('anthropic-api-key')
        PUSHGATEWAY_URL   = 'http://pushgateway:9091'
        BUILD_START_MS    = "${System.currentTimeMillis()}"
    }

    options {
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
        buildDiscarder(logRotator(numToKeepStr: '50'))
    }

    stages {

        // ── Stage 1: Checkout ────────────────────────────────────────────
        stage('Checkout') {
            steps {
                checkout scm
                sh 'mkdir -p reports'
            }
        }

        // ── Stage 2: Secret Scan ─────────────────────────────────────────
        // detect-secrets scans the workspace for hardcoded credentials.
        // Any finding causes the pipeline to FAIL and the metric
        // secret_leak_attempts_total is incremented in Grafana.
        stage('Secret Scan') {
            steps {
                sh '''
                    if [ -f .secrets.baseline ]; then
                        # Audit mode: only flag secrets NOT in the baseline
                        detect-secrets scan \
                          --exclude-files '\\.env\\.example$' \
                          --exclude-files '\\.secrets\\.baseline$' \
                          > reports/secrets_all.json 2>/dev/null || true
                        detect-secrets audit --diff .secrets.baseline reports/secrets_all.json \
                          > reports/secrets.json 2>/dev/null || \
                        python3 -c "
import json
baseline = json.load(open('.secrets.baseline'))
current  = json.load(open('reports/secrets_all.json'))
new_findings = {}
for fname, findings in current.get('results', {}).items():
    baseline_hashes = {f['hashed_secret'] for f in baseline.get('results', {}).get(fname, [])}
    new_ones = [f for f in findings if f['hashed_secret'] not in baseline_hashes]
    if new_ones:
        new_findings[fname] = new_ones
print(json.dumps({'results': new_findings}, indent=2))
" > reports/secrets.json
                    else
                        detect-secrets scan \
                          --exclude-files '\\.env\\.example$' \
                          --exclude-files '\\.secrets\\.baseline$' \
                          > reports/secrets.json 2>/dev/null || true
                    fi
                '''
            }
            post {
                always {
                    script {
                        def rc = sh(
                            script: 'python3 scripts/count_secrets.py',
                            returnStatus: true
                        )
                        archiveArtifacts artifacts: 'reports/secrets.json',
                                         allowEmptyArchive: true
                        if (rc != 0) {
                            // Push failure metric before aborting
                            def secretCount = sh(
                                script: 'cat reports/secret_count.txt 2>/dev/null || echo 1',
                                returnStdout: true
                            ).trim()
                            def branch = env.GIT_BRANCH?.replaceAll('^origin/', '') ?: env.BRANCH_NAME ?: 'unknown'
                            sh """
                                PUSHGATEWAY_URL=${PUSHGATEWAY_URL} \
                                python3 scripts/metrics_exporter.py \
                                  --job "build_${env.BUILD_NUMBER}_secret_fail" \
                                  --branch "${branch}" \
                                  --developer "Dev One" \
                                  --ai-tool claude_code \
                                  --duration 0 \
                                  --secret-count ${secretCount} || true
                            """
                            error('SECRET SCAN FAILED: Hardcoded credentials detected. See reports/secrets.json')
                        }
                    }
                }
            }
        }

        // ── Stage 3: SAST ────────────────────────────────────────────────
        stage('SAST') {
            steps {
                sh '''
                    semgrep \
                      --config=p/python \
                      --config=p/owasp-top-ten \
                      --json \
                      --output reports/semgrep.json \
                      app/src/ || true
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'reports/semgrep.json',
                                     allowEmptyArchive: true
                }
            }
        }

        // ── Stage 4: AI Policy Check ─────────────────────────────────────
        stage('AI Policy Check') {
            steps {
                sh "python3 scripts/ai_policy_check.py --branch ${env.BRANCH_NAME ?: 'HEAD'}"
            }
        }

        // ── Stage 5: Tests ───────────────────────────────────────────────
        stage('Tests') {
            environment {
                PYTHONPATH = "${env.WORKSPACE}/app/src"
            }
            steps {
                sh '''
                    python3 -m pytest app/tests/ \
                      --cov=app/src \
                      --cov-report=xml:reports/coverage.xml \
                      --cov-report=html:reports/coverage_html \
                      --junitxml=reports/test-results.xml \
                      -v
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true,
                          testResults: 'reports/test-results.xml'
                    archiveArtifacts artifacts: 'reports/coverage.xml,reports/test-results.xml',
                                     allowEmptyArchive: true
                }
            }
        }

        // ── Stage 6: Push Metrics ────────────────────────────────────────
        stage('Push Metrics') {
            steps {
                script {
                    def durationSecs = (System.currentTimeMillis() - env.BUILD_START_MS.toLong()) / 1000.0

                    def coveragePct = sh(
                        script: '''python3 -c "
import xml.etree.ElementTree as ET, sys
try:
    root = ET.parse('reports/coverage.xml').getroot()
    print(float(root.get('line-rate', '0')) * 100)
except Exception:
    print(0)
" ''',
                        returnStdout: true
                    ).trim()

                    def secretCount = sh(
                        script: 'cat reports/secret_count.txt 2>/dev/null || echo 0',
                        returnStdout: true
                    ).trim()

                    def sastLine = sh(
                        script: 'python3 scripts/parse_semgrep.py 2>/dev/null || echo "0,0,0"',
                        returnStdout: true
                    ).trim()
                    def sast = sastLine.split(',')

                    sh """
                        PUSHGATEWAY_URL=${PUSHGATEWAY_URL} \
                        python3 scripts/metrics_exporter.py \
                          --job "build_${env.BUILD_NUMBER}" \
                          --branch "${env.BRANCH_NAME ?: 'unknown'}" \
                          --developer "Dev One" \
                          --ai-tool claude_code \
                          --duration ${durationSecs} \
                          --success \
                          --coverage ${coveragePct} \
                          --sast-high ${sast[0]} \
                          --sast-medium ${sast[1]} \
                          --secret-count ${secretCount}
                    """
                }
            }
        }
    }

    // ── Post-Pipeline ────────────────────────────────────────────────────
    post {
        failure {
            script {
                def branch = env.GIT_BRANCH?.replaceAll('^origin/', '') ?: env.BRANCH_NAME ?: 'unknown'
                echo "Pipeline FAILED on branch: ${branch}"
                def durationSecs = (System.currentTimeMillis() - env.BUILD_START_MS.toLong()) / 1000.0
                def secretCount = sh(
                    script: 'cat reports/secret_count.txt 2>/dev/null || echo 0',
                    returnStdout: true
                ).trim()
                sh """
                    PUSHGATEWAY_URL=${PUSHGATEWAY_URL} \
                    python3 scripts/metrics_exporter.py \
                      --job "build_${env.BUILD_NUMBER}_failed" \
                      --branch "${branch}" \
                      --developer "Dev One" \
                      --ai-tool claude_code \
                      --duration ${durationSecs} \
                      --secret-count ${secretCount} || true
                """
            }
        }
        cleanup {
            cleanWs()
        }
    }
}
