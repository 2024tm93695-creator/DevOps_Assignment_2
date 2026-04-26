pipeline {
    agent any

    environment {
        DOCKER_HUB_REPO   = "prasannamanne/aceest-fitness"
        DOCKER_CREDENTIALS = credentials('dockerhub-credentials')
        SONAR_HOST_URL    = "https://sonarcloud.io"
        SONAR_TOKEN       = credentials('sonarcloud-token')
        APP_VERSION       = "3.2.4"
        IMAGE_TAG         = "${APP_VERSION}-${BUILD_NUMBER}"
        KUBECONFIG        = credentials('kubeconfig')
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }

    stages {

        // ------------------------------------------------------------------
        stage('Checkout') {
        // ------------------------------------------------------------------
            steps {
                checkout scm
                echo "Branch: ${env.GIT_BRANCH} | Commit: ${env.GIT_COMMIT?.take(8)}"
            }
        }

        // ------------------------------------------------------------------
        stage('Install Dependencies') {
        // ------------------------------------------------------------------
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        // ------------------------------------------------------------------
        stage('Unit Tests') {
        // ------------------------------------------------------------------
            steps {
                sh '''
                    . venv/bin/activate
                    pytest tests/ \
                        --junitxml=reports/junit.xml \
                        --cov=app \
                        --cov-report=xml:reports/coverage.xml \
                        --cov-report=html:reports/htmlcov \
                        -v
                '''
            }
            post {
                always {
                    junit 'reports/junit.xml'
                    publishHTML(target: [
                        reportDir  : 'reports/htmlcov',
                        reportFiles: 'index.html',
                        reportName : 'Coverage Report'
                    ])
                }
            }
        }

        // ------------------------------------------------------------------
        stage('SonarCloud Analysis') {
        // ------------------------------------------------------------------
            steps {
                withSonarQubeEnv('SonarCloud') {
                    sh '''
                        sonar-scanner \
                            -Dsonar.token=${SONAR_TOKEN}
                    '''
                }
            }
        }

        // ------------------------------------------------------------------
        stage('Quality Gate') {
        // ------------------------------------------------------------------
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    waitForQualityGate abortPipeline: true
                }
            }
        }

        // ------------------------------------------------------------------
        stage('Build Docker Image') {
        // ------------------------------------------------------------------
            steps {
                sh """
                    docker build \
                        --build-arg APP_VERSION=${APP_VERSION} \
                        -t ${DOCKER_HUB_REPO}:${IMAGE_TAG} \
                        -t ${DOCKER_HUB_REPO}:latest \
                        .
                """
            }
        }

        // ------------------------------------------------------------------
        stage('Push Docker Image') {
        // ------------------------------------------------------------------
            steps {
                sh """
                    echo "${DOCKER_CREDENTIALS_PSW}" | \
                        docker login -u "${DOCKER_CREDENTIALS_USR}" --password-stdin
                    docker push ${DOCKER_HUB_REPO}:${IMAGE_TAG}
                    docker push ${DOCKER_HUB_REPO}:latest
                """
            }
        }

        // ------------------------------------------------------------------
        stage('Deploy – Rolling Update') {
        // ------------------------------------------------------------------
            when { branch 'main' }
            steps {
                sh """
                    kubectl set image deployment/aceest-fitness \
                        aceest-fitness=${DOCKER_HUB_REPO}:${IMAGE_TAG} \
                        --record
                    kubectl rollout status deployment/aceest-fitness --timeout=120s
                """
            }
        }

        // ------------------------------------------------------------------
        stage('Deploy – Canary (10 %)') {
        // ------------------------------------------------------------------
            when { branch 'release/*' }
            steps {
                sh """
                    # Update canary image and scale to 1 replica (≈10 % traffic)
                    kubectl set image deployment/aceest-fitness-canary \
                        aceest-fitness=${DOCKER_HUB_REPO}:${IMAGE_TAG} --record
                    kubectl scale deployment/aceest-fitness-canary --replicas=1
                    kubectl rollout status deployment/aceest-fitness-canary --timeout=120s
                    echo "Canary deployed with image ${IMAGE_TAG}"
                """
            }
        }

        // ------------------------------------------------------------------
        stage('Smoke Test') {
        // ------------------------------------------------------------------
            when { branch 'main' }
            steps {
                sh '''
                    # Wait for pod readiness then hit health endpoint
                    sleep 10
                    kubectl run smoke-test --image=curlimages/curl:8.7.1 \
                        --rm --restart=Never \
                        -- curl -sf http://aceest-fitness-svc/health
                '''
            }
        }
    }

    post {
        success {
            echo "Pipeline SUCCESS – Image: ${DOCKER_HUB_REPO}:${IMAGE_TAG}"
        }
        failure {
            echo "Pipeline FAILED – rolling back deployment"
            sh '''
                kubectl rollout undo deployment/aceest-fitness || true
            '''
        }
        always {
            sh 'docker rmi ${DOCKER_HUB_REPO}:${IMAGE_TAG} || true'
            cleanWs()
        }
    }
}
