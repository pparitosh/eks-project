variable "aws_region" { default = "ap-south-1" }
variable "cluster_name" {
  type    = string
  default = "tf-eks-cluster"
}
variable "vpc_id" {
  type = string
  default = "vpc-0d3670586e6ff4508"
}

variable "public_subnets" { 
    type = list
    default = ["subnet-049612bebb33564d1", "subnet-0a1da9a92fdf9cae8"]
    }
variable "private_subnets" { 
    type = list
    default = ["subnet-050dde9bd0ae229a4", "subnet-011b40c987c4e6daf"] 
    }
variable "node_instance_types" { default = ["t2.medium"] }
variable "desired_capacity" { default = 3 }
variable "key_pair" { default = "my-eks-project"}
variable "iam_role_arn" {default = "arn:aws:iam::931895328127:role/eksctl-testcluster-cluster-ServiceRole-1SFKIB645Y9P0"}
variable "eks_node_role" {default = "arn:aws:iam::931895328127:role/NewClusterSelfmanaged-NodeInstanceRole-10P8AWMRBJ9FZ"}
