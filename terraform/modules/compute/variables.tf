variable "subnet_id" {
  description = "Subnet ID for the application server"
  type        = string
}

variable "security_group_id" {
  description = "Security group ID for the application server"
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
}

variable "app_port" {
  description = "Port exposed by the application"
  type        = number
}

variable "app_repository_url" {
  description = "Git repository for the application code"
  type        = string
}

variable "root_volume_size_gb" {
  description = "Root volume size for the application server"
  type        = number
}

variable "availability_zone" {
  description = "Availability zone for the instance"
  type        = string
}
