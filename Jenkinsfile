pipeline {
  agent any
  options { timestamps() }

  environment {
    PATH              = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
    AWS_DEFAULT_REGION = 'us-west-2'
    CLUSTER_NAME       = 'dev-eks'
    K8S_NAMESPACE      = 'demo'
    ECR_REPO           = 'jenkins-eks-demo'
    KUBECONFIG         = "${WORKSPACE}/kubeconfig"
  }

  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('AWS Auth') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'aws-creds',
                  usernameVariable: 'AWS_ACCESS_KEY_ID',
                  passwordVariable: 'AWS_SECRET_ACCESS_KEY')]) {
          sh 'aws sts get-caller-identity'
        }
      }
    }

    stage('ECR Setup & Login') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'aws-creds',
                  usernameVariable: 'AWS_ACCESS_KEY_ID',
                  passwordVariable: 'AWS_SECRET_ACCESS_KEY')]) {
          sh '''
            set -e
            ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
            ECR_URI="$ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com/$ECR_REPO"
            echo "ECR_URI=$ECR_URI" > .ecr.env

            aws ecr describe-repositories --repository-names "$ECR_REPO" >/dev/null 2>&1 || \
            aws ecr create-repository --repository-name "$ECR_REPO" --image-scanning-configuration scanOnPush=true

            aws ecr get-login-password | docker login --username AWS --password-stdin "$ACCOUNT_ID.dkr.ecr.$AWS_DEFAULT_REGION.amazonaws.com"
          '''
        }
      }
    }

    stage('Build & Push Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'aws-creds',
                  usernameVariable: 'AWS_ACCESS_KEY_ID',
                  passwordVariable: 'AWS_SECRET_ACCESS_KEY')]) {
          sh '''
            set -e
            . .ecr.env
            IMAGE_TAG="${GIT_COMMIT}"
            docker build -t "$ECR_URI:$IMAGE_TAG" .
            docker push "$ECR_URI:$IMAGE_TAG"
            docker tag "$ECR_URI:$IMAGE_TAG" "$ECR_URI:latest" || true
            docker push "$ECR_URI:latest" || true
            echo "IMAGE=$ECR_URI:$IMAGE_TAG" > .image.env
          '''
        }
      }
    }

    stage('Kubeconfig') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'aws-creds',
                  usernameVariable: 'AWS_ACCESS_KEY_ID',
                  passwordVariable: 'AWS_SECRET_ACCESS_KEY')]) {
          sh '''
            aws eks update-kubeconfig \
              --name "$CLUSTER_NAME" \
              --region "$AWS_DEFAULT_REGION" \
              --kubeconfig "$KUBECONFIG" \
              --alias "$CLUSTER_NAME"

            kubectl --kubeconfig "$KUBECONFIG" get nodes -o wide
          '''
        }
      }
    }

    stage('Deploy to EKS') {
      steps {
        sh '''
          set -e
          source .image.env
          kubectl --kubeconfig "$KUBECONFIG" apply -f k8s/namespace.yaml
          IMAGE="$IMAGE" envsubst < k8s/deployment.tmpl.yaml > k8s/deployment.yaml
          kubectl --kubeconfig "$KUBECONFIG" -n "$K8S_NAMESPACE" apply -f k8s/deployment.yaml -f k8s/service.yaml
          kubectl --kubeconfig "$KUBECONFIG" -n "$K8S_NAMESPACE" rollout status deploy/web --timeout=120s
        '''
      }
    }

    stage('Show Endpoint') {
      steps {
        sh '''
          echo "Service hostname (may take a minute):"
          kubectl --kubeconfig "$KUBECONFIG" -n "$K8S_NAMESPACE" \
            get svc web -o jsonpath="{.status.loadBalancer.ingress[0].hostname}{\"\\n\"}" || true
        '''
      }
    }
  }

  post {
    always {
      archiveArtifacts artifacts: 'k8s/deployment.yaml', allowEmptyArchive: true
    }
  }
}
