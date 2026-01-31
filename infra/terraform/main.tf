module "eks" {
  source = "terraform-aws-modules/eks/aws"
  version = "~> 21.0"
  name    = var.cluster_name
  kubernetes_version = "1.33"
  subnet_ids         = var.private_subnets
  endpoint_public_access = true
  vpc_id          = var.vpc_id
  create_iam_role = false
  iam_role_arn    = var.iam_role_arn
  tags = {
    Environment = "dev"
    Terraform   = "true"
  }

  enable_irsa = true
}

# ---------------------------
# EKS Managed Addons
# ---------------------------
resource "aws_eks_addon" "vpc_cni" {
  cluster_name = module.eks.cluster_name
  addon_name   = "vpc-cni"
}

resource "aws_eks_addon" "coredns" {
  cluster_name = module.eks.cluster_name
  addon_name   = "coredns"
  depends_on   = [aws_eks_node_group.default] # CoreDNS needs nodes to run
}

resource "aws_eks_addon" "kube_proxy" {
  cluster_name = module.eks.cluster_name
  addon_name   = "kube-proxy"
}

resource "aws_eks_addon" "metrics_server" {
  cluster_name = module.eks.cluster_name
  addon_name   = "metrics-server"
  # Optional: specify a version or let EKS manage it
  # addon_version = "v0.6.1" 
}

resource "aws_eks_addon" "cloudwatch_observability" {
  cluster_name = module.eks.cluster_name
  addon_name   = "amazon-cloudwatch-observability"
  
  # Ensure the node group exists so the daemonset has somewhere to deploy
  depends_on = [aws_eks_node_group.default]
}

# ---------------------------
# Managed Node Group (AL2023)
# ---------------------------
resource "aws_eks_node_group" "default" {
  cluster_name    = module.eks.cluster_name
  node_group_name = "managed-ng-al2023" # Your custom name
  node_role_arn   = var.eks_node_role
  subnet_ids      = var.private_subnets
  remote_access {
  ec2_ssh_key     = var.key_pair
  }
  # Amazon Linux 2023
  ami_type       = "AL2023_x86_64_STANDARD"
  instance_types = var.node_instance_types

  scaling_config {
    desired_size = var.desired_capacity
    min_size     = 1
    max_size     = 4
  }

  capacity_type = "ON_DEMAND"
}

# --------------------------------------
# Extra policies to node role
# --------------------------------------
resource "aws_iam_role_policy_attachment" "cloudwatch_observability" {
  policy_arn = "arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy"
  role       = element(split("/", var.eks_node_role), length(split("/", var.eks_node_role)) - 1) # The name of your node role
}

# ---------------------------
# ECR repository
# ---------------------------
resource "aws_ecr_repository" "app" {
  name                 = "flask-app-repo"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
}

# ---------------------------
# Outputs
# ---------------------------
output "ecr_repository_url" { value = aws_ecr_repository.app.repository_url }