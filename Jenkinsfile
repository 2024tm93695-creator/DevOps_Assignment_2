pipeline {
    agent any

    environment {
        DOCKER_HUB_REPO = "prasannamanne/aceest-fitness"
        SONAR_HOST_URL  = "https://sonarcloud.io"
        APP_VERSION     = "3.2.4"
        IMAGE_TAG       = "${APP_VERSION}-${BUILD_NUMBER}"
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        timestamps()
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                echo "Branch: ${env.GIT_BRANCH} | Commit: ${env.GIT_COMMIT?.take(8)}"
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install --upgrade pip
                    pip install -r requirements.txt
                '''
            }
        }

        stage('Unit Tests') {
            steps {
                sh '''
                    . venv/bin/activate
                    mkdir -p reports
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
                }
            }
        }

        stage('SonarQube Analysis') {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    withCredentials([string(credentialsId: 'sonarcloud-token', variable: 'SONAR_TOKEN')]) {
                        sh '''
                            sonar-scanner \
                                -Dsonar.host.url=http://host.docker.internal:9000 \
                                -Dsonar.token=${SONAR_TOKEN}
                        '''
                    }
                }
            }
        }

        stage('Quality Gate') {
            steps {
                catchError(buildResult: 'SUCCESS', stageResult: 'UNSTABLE') {
                    timeout(time: 5, unit: 'MINUTES') {
                        waitForQualityGate abortPipeline: false
                    }
                }
            }
        }

        stage('Build Docker Image') {
            steps {
                sh """
                    docker build \\
                        --build-arg APP_VERSION=${APP_VERSION} \\
                        -t ${DOCKER_HUB_REPO}:${IMAGE_TAG} \\
                        -t ${DOCKER_HUB_REPO}:latest \\
                        .
                """
            }
        }

        stage('Push Docker Image') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-credentials',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh """
                        echo "${DOCKER_PASS}" | docker login -u "${DOCKER_USER}" --password-stdin
                        docker push ${DOCKER_HUB_REPO}:${IMAGE_TAG}
                        docker push ${DOCKER_HUB_REPO}:latest
                    """
                }
            }
        }

        stage('Deploy – Rolling Update') {
            when { branch 'main' }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh """
                        kubectl set image deployment/aceest-fitness \\
                            aceest-fitness=${DOCKER_HUB_REPO}:${IMAGE_TAG}
                        kubectl rollout status deployment/aceest-fitness --timeout=120s
                    """
                }
            }
        }

        stage('Deploy – Canary (10%)') {
            when { branch 'release/*' }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh """
                        kubectl set image deployment/aceest-fitness-canary \\
                            aceest-fitness=${DOCKER_HUB_REPO}:${IMAGE_TAG}
                        kubectl scale deployment/aceest-fitness-canary --replicas=1
                        kubectl rollout status deployment/aceest-fitness-canary --timeout=120s
                    """
                }
            }
        }

        stage('Smoke Test') {
            when { branch 'main' }
            steps {
                withCredentials([file(credentialsId: 'kubeconfig', variable: 'KUBECONFIG')]) {
                    sh '''
                        sleep 10
                        kubectl run smoke-test --image=curlimages/curl:8.7.1 \
                            --rm --restart=Never \
                            -- curl -sf http://aceest-fitness-svc/health
                    '''
                }
            }
        }
    }

    post {
        success {
            echo "Pipeline SUCCESS – Image: ${DOCKER_HUB_REPO}:${IMAGE_TAG}"
        }
        failure {
            echo "Pipeline FAILED"
        }
        always {
            sh "docker rmi ${DOCKER_HUB_REPO}:${IMAGE_TAG} || true"
            cleanWs()
        }
    }
}
