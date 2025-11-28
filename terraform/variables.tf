variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-west-2"
}

variable "availability_zone_a" {
  description = "Primary availability zone for private subnet A"
  type        = string
  default     = "us-west-2a"
}

variable "availability_zone_b" {
  description = "Secondary availability zone for private subnet B"
  type        = string
  default     = "us-west-2b"
}

variable "default_public_subnet_az" {
  description = "Availability zone to pick the default public subnet for the app server"
  type        = string
  default     = "us-west-2a"
}

variable "private_subnet_a_cidr" {
  description = "CIDR block for the first private subnet"
  type        = string
  default     = "172.31.96.0/20"
}

variable "private_subnet_b_cidr" {
  description = "CIDR block for the second private subnet"
  type        = string
  default     = "172.31.112.0/20"
}

variable "app_ingress_cidr" {
  description = "CIDR block allowed to reach the application"
  type        = string
  default     = "0.0.0.0/0"
}

variable "app_port" {
  description = "Port the application listens on"
  type        = number
  default     = 8501
}

variable "db_name" {
  description = "PostgreSQL database name"
  type        = string
  default     = "financeapp"
}

variable "db_username" {
  description = "PostgreSQL master username"
  type        = string
  default     = "finance_admin"
}

variable "db_kms_key_arn" {
  description = "Optional KMS key ARN to encrypt the PostgreSQL instance (uses AWS-managed key by default)"
  type        = string
  default     = null
}

variable "instance_type" {
  description = "EC2 instance type for the application server"
  type        = string
  default     = "t3.micro"
}

variable "root_volume_size_gb" {
  description = "Root EBS volume size for the application server"
  type        = number
  default     = 20
}

variable "app_repository_url" {
  description = "Git repository to clone for the application"
  type        = string
  default     = "https://github.com/rakeshsurya-cloud/personal_finance_tracker.git"
}
