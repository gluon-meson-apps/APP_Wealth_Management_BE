def GM_SDK_GIT_SSH_KEY_CREDS_ID='svc-gluon-meson'

pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Lint & Test') {
            steps {
                script {
                    sshagent (credentials: ["${GM_SDK_GIT_SSH_KEY_CREDS_ID}"]) {
                        sh 'curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python3 -'
                        sh '/opt/poetry/bin/poetry env use python3.9'
                        sh '/opt/poetry/bin/poetry install'
                        sh '/opt/poetry/bin/poetry run make lint'
                        sh '/opt/poetry/bin/poetry run make test'
                    }
                }

            }
        }

        stage('Build Docker Image') {
            steps {
                script {
                    withCredentials([sshUserPrivateKey(credentialsId: "${GM_SDK_GIT_SSH_KEY_CREDS_ID}", keyFileVariable: "GM_SDK_GIT_SSH_KEY")]) {
                        sh "eval \"\$(ssh-agent -s)\" && ssh-add ${GM_SDK_GIT_SSH_KEY}"
                        sh "GM_SDK_GIT_SSH_KEY=${GM_SDK_GIT_SSH_KEY} docker compose build"
                    }
                }
            }
        }

        stage('Run Docker Container') {
            steps {
                script {
                    sh 'docker compose down'
                    sh 'docker compose up -d'
                }
            }
        }
    }
}