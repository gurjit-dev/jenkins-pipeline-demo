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
        source .ecr.env
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
