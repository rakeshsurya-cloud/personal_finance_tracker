variable "vpc_id" {
  description = "VPC ID for security groups"
  type        = string
}

variable "app_port" {
  description = "Port exposed by the application server"
  type        = number
}

variable "app_ingress_cidr" {
  description = "CIDR block allowed to access the application"
  type        = string
}
