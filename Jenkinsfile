pipeline {
    agent any

    environment {
        IMAGE_NAME = 'sentiment-ai'
        REGISTRY = 'ghcr.io/olivierpolynice'
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm

                script {
                    env.IMAGE_TAG = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                }

                echo "Commit : ${env.GIT_COMMIT}"
                echo "Tag image : ${env.IMAGE_TAG}"

                sh 'git log --oneline -5'
            }
        }

        stage('Lint') {
            steps {
                sh '''
                    docker run --rm \
                    --volumes-from jenkins \
                    -w "$WORKSPACE" \
                    python:3.12-slim \
                    sh -c "pip install flake8 -q && flake8 src/ --max-line-length=100"
                '''
            }
        }

        stage('IaC Validate') {
            steps {
                dir('infra') {
                    sh '''
                        terraform init -backend=false -input=false
                        terraform fmt -check
                        terraform validate
                    '''
                }
            }
        }

        stage('Build & Test') {
            steps {
                sh '''
                    docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

                    docker rm -f test-runner 2>/dev/null || true

                    set +e

                    docker run \
                    -e CI=true \
                    --name test-runner \
                    ${IMAGE_NAME}:${IMAGE_TAG} \
                    pytest tests/ -v \
                    --cov=src \
                    --cov-report=xml:/tmp/coverage.xml \
                    --cov-report=term-missing \
                    --cov-fail-under=70

                    TEST_EXIT_CODE=$?

                    set -e

                    docker cp test-runner:/tmp/coverage.xml ./coverage.xml 2>/dev/null || true
                    docker rm -f test-runner 2>/dev/null || true

                    exit $TEST_EXIT_CODE
                '''
            }

            post {
                failure {
                    echo 'Tests échoués ou couverture insuffisante (< 70 %).'
                }
            }
        }

        stage('SonarQube Analysis') {
            environment {
                SONARQUBE_TOKEN = credentials('sonar-token')
            }

            steps {
                withSonarQubeEnv('sonarqube') {
                    sh '''
                        docker run --rm \
                        --network cicd-network \
                        --volumes-from jenkins \
                        -w "$WORKSPACE" \
                        -e SONAR_HOST_URL="$SONAR_HOST_URL" \
                        -e SONAR_TOKEN="$SONARQUBE_TOKEN" \
                        sonarsource/sonar-scanner-cli:latest \
                        sonar-scanner \
                        -Dsonar.projectKey=sentiment-ai \
                        -Dsonar.projectName=SentimentAI \
                        -Dsonar.projectBaseDir="$WORKSPACE" \
                        -Dsonar.sources=src \
                        -Dsonar.tests=tests \
                        -Dsonar.python.version=3.11 \
                        -Dsonar.python.coverage.reportPaths=coverage.xml \
                        -Dsonar.sourceEncoding=UTF-8 \
                        -Dsonar.scanner.metadataFilePath="$WORKSPACE/report-task.txt"
                    '''
                }
            }
        }

        stage('Quality Gate') {
            steps {
                timeout(time: 15, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        stage('Security Scan') {
            steps {
                sh '''
                    docker run --rm \
                    -v /var/run/docker.sock:/var/run/docker.sock \
                    -v trivy-cache:/root/.cache/trivy \
                    aquasec/trivy:latest image \
                    --severity HIGH,CRITICAL \
                    --exit-code 0 \
                    --format table \
                    ${IMAGE_NAME}:${IMAGE_TAG}
                '''
            }

            post {
                success {
                    echo 'Analyse Trivy terminée.'
                }
            }
        }

        stage('Push') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'github-token',
                        usernameVariable: 'REGISTRY_USER',
                        passwordVariable: 'REGISTRY_PASS'
                    )
                ]) {
                    sh '''
                        echo "$REGISTRY_PASS" | docker login ghcr.io \
                        -u "$REGISTRY_USER" \
                        --password-stdin

                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                        docker tag ${IMAGE_NAME}:${IMAGE_TAG} ${REGISTRY}/${IMAGE_NAME}:latest

                        docker push ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}
                        docker push ${REGISTRY}/${IMAGE_NAME}:latest
                    '''
                }
            }
        }

        stage('IaC Apply') {
            steps {
                dir('infra') {
                    sh '''
                        terraform init -input=false

                        if ! terraform state list 2>/dev/null | grep -qx "docker_network.cicd"; then
                            NETWORK_ID=$(docker network inspect cicd-network --format '{{.Id}}')

                            terraform import \
                            -var="docker_host=unix:///var/run/docker.sock" \
                            docker_network.cicd "$NETWORK_ID"
                        fi

                        if ! terraform state list 2>/dev/null | grep -qx "docker_container.sentiment_staging"; then
                            docker rm -f sentiment-staging 2>/dev/null || true
                        fi

                        terraform apply -auto-approve \
                        -var="image_tag=${IMAGE_TAG}" \
                        -var="docker_host=unix:///var/run/docker.sock"
                    '''
                }
            }
        }

        stage('Deploy Staging') {
            steps {
                sh '''
                    for attempt in 1 2 3 4 5 6 7 8 9 10; do
                        if docker run --rm \
                        --network cicd-network \
                        curlimages/curl:8.7.1 \
                        -fsS http://sentiment-staging:8000/health; then
                            exit 0
                        fi

                        echo "API non prête, nouvelle tentative dans 3 secondes..."
                        sleep 3
                    done

                    exit 1
                '''

                echo 'Staging vérifié avec succès.'
            }
        }
    }

    post {
        always {
            sh '''
                docker rm -f test-runner 2>/dev/null || true
            '''
        }

        success {
            echo "Pipeline réussi."
            echo "Image publiée et déployée par Terraform : ${REGISTRY}/${IMAGE_NAME}:${IMAGE_TAG}"
        }

        failure {
            echo 'Pipeline échoué. Consulte les logs du stage concerné.'
        }
    }
}