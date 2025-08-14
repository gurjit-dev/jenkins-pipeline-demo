pipeline {
  agent any
  options { timestamps() }

  environment {
    PATH               = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
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
          script {
            env.ACCOUNT_ID = sh(
              script: "aws sts get-caller-identity --query Account --output text",
              returnStdout: true
            ).trim()
            env.ECR_URI = "${env.ACCOUNT_ID}.dkr.ecr.${env.AWS_DEFAULT_REGION}.amazonaws.com/${env.ECR_REPO}"
          }
          sh '''
            set -e
            aws ecr describe-repositories --repository-names "$ECR_REPO" >/dev/null 2>&1 || \
            aws ecr create-repository --repository-name "$ECR_REPO" --image-scanning-configuration scanOnPush=true

            aws ecr get-login-password | docker login --username AWS --password-stdin \
              "${ACCOUNT_ID}.dkr.ecr.${AWS_DEFAULT_REGION}.amazonaws.com"
          '''
        }
      }
    }

    stage('Build & Push Image') {
      steps {
        withCredentials([usernamePassword(credentialsId: 'aws-creds',
                  usernameVariable: 'AWS_ACCESS_KEY_ID',
                  passwordVariable: 'AWS_SECRET_ACCESS_KEY')]) {
          script {
            env.IMAGE = "${env.ECR_URI}:${env.GIT_COMMIT}"
          }
          sh '''
            set -e
            docker build -t "$IMAGE" .
            docker push "$IMAGE"
            docker tag "$IMAGE" "${ECR_URI}:latest" || true
            docker push "${ECR_URI}:latest" || true
          '''
        }
      }
    }

    stage('Allow Jenkins -> EKS API') {
  steps {
    withCredentials([usernamePassword(credentialsId: 'aws-creds',
      usernameVariable: 'AWS_ACCESS_KEY_ID',
      passwordVariable: 'AWS_SECRET_ACCESS_KEY')]) {
      sh '''
        set -e
        REGION="$AWS_DEFAULT_REGION"
        CLUSTER="$CLUSTER_NAME"

        INSTANCE_ID=$(curl -s http://169.254.169.254/latest/meta-data/instance-id)
        CLUSTER_SG=$(aws eks describe-cluster --name "$CLUSTER" --region "$REGION" \
          --query "cluster.resourcesVpcConfig.clusterSecurityGroupId" --output text)
        JENKINS_SG=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" --region "$REGION" \
          --query "Reservations[0].Instances[0].SecurityGroups[0].GroupId" --output text)

        echo "Cluster SG:  $CLUSTER_SG"
        echo "Jenkins  SG: $JENKINS_SG"

        # Allow HTTPS from Jenkins SG to the EKS control plane
        aws ec2 authorize-security-group-ingress \
          --group-id "$CLUSTER_SG" --protocol tcp --port 443 --source-group "$JENKINS_SG" \
          --region "$REGION" || true
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
          kubectl --kubeconfig "$KUBECONFIG" apply -f k8s/namespace.yaml
          IMAGE="$IMAGE" envsubst < k8s/deployment.tmpl.yaml > k8s/deployment.yaml
          kubectl --kubeconfig "$KUBECONFIG" -n "$K8S_NAMESPACE" apply \
            -f k8s/deployment.yaml -f k8s/service.yaml
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
