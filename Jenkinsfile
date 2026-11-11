pipeline {
    agent any
    environment {
        IMAGE_NAME = 'dailynest-api'
    }
    stages {
        stage('Checkout') {
            steps { checkout scm }
        }
        stage('Python environment') {
            steps {
                sh 'python3 --version'
                sh 'python3 -m venv .venv'
                sh '. .venv/bin/activate && pip install -r requirements.txt'
            }
        }
        stage('Test') {
            steps {
                sh '. .venv/bin/activate && pytest -q'
            }
        }
        stage('Build Docker image') {
            steps {
                sh 'docker build -t ${IMAGE_NAME}:${BUILD_NUMBER} .'
            }
        }
    }
    post {
        success { echo 'DailyNest CI stages completed successfully.' }
        failure { echo 'Pipeline failed. Review the failed stage logs.' }
    }
}
