variable "vpc_id" {
  description = "VPC ID where private subnets will be created"
  type        = string
}

variable "availability_zone_a" {
  description = "Availability zone for the first private subnet"
  type        = string
}

variable "availability_zone_b" {
  description = "Availability zone for the second private subnet"
  type        = string
}

variable "private_subnet_a_cidr" {
  description = "CIDR block for private subnet A"
  type        = string
}

variable "private_subnet_b_cidr" {
  description = "CIDR block for private subnet B"
  type        = string
}
