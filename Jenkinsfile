pipeline {
    agent any

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
//
//         stage('Lint & Test') {
//             steps {
//                 script {
//                     sh 'curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python3 -'
//                     sh '/opt/poetry/bin/poetry install'
//                     sh '/opt/poetry/bin/poetry run make lint'
//                     sh '/opt/poetry/bin/poetry run make test'
//                 }
//             }
//         }

        stage('Build Docker Image') {
            steps {
                script {
                    sh 'docker compose build'
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