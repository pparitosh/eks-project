# eks-project
EKS project to load test and CRD for nodes

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=YOUR_AWS_REGION
REPO=flask-app-repo
ECR_URI="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com/${REPO}"

# Create repository (if Terraform didn't)
aws ecr create-repository --repository-name ${REPO} --region ${REGION} || true

# Docker login
aws ecr get-login-password --region ${REGION} | docker login --username AWS --password-stdin ${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com

# Build, tag, push
docker build -t ${REPO}:v1 app/flask_app
docker tag ${REPO}:v1 ${ECR_URI}:v1
docker push ${ECR_URI}:v1

# Apply all required objects
kubectl apply -f k8s/base/deployment.yaml
kubectl apply -f k8s/base/service.yaml
kubectl apply -f k8s/base/hpa.yaml
kubectl get svc flask-service
kubectl get hpa

# Stress Command
kubectl run -i --tty load-generator --rm --image=busybox:1.28 --restart=Never -- /bin/sh -c "while sleep 0.01; do wget -q -O- http://flask-service; done" >/dev/null 2>&1

# Check hpa
$ kubectl get hpa -w
```
NAME        REFERENCE              TARGETS       MINPODS   MAXPODS   REPLICAS   AGE
flask-hpa   Deployment/flask-app   cpu: 2%/50%   2         10        2          144m
flask-hpa   Deployment/flask-app   cpu: 23%/50%   2         10        2          144m
flask-hpa   Deployment/flask-app   cpu: 61%/50%   2         10        2          144m
flask-hpa   Deployment/flask-app   cpu: 45%/50%   2         10        3          144m
flask-hpa   Deployment/flask-app   cpu: 37%/50%   2         10        3          144m
```

# Observability
- Choose to install cloudwatch observability.
Components: 
CW agent: Metrics
Fluentbit : Logs

Dashboards: Cloudwatch

