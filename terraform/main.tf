terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 4.16"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  required_version = ">= 1.2.0"
}

provider "aws" {
  region = var.aws_region
}

# --- Shared Resources ---

resource "random_password" "db_password" {
  length           = 20
  special          = true
  override_special = "!#$%&*+-=?@^_"
  min_numeric      = 4
  min_upper        = 2
  min_lower        = 2
}

resource "aws_kms_key" "rds" {
  description         = "KMS key for encrypting the RDS PostgreSQL instance"
  enable_key_rotation = true
}

resource "aws_kms_alias" "rds" {
  name          = "alias/finance-rds"
  target_key_id = aws_kms_key.rds.id
}

# --- Data Sources ---

data "aws_vpc" "default" {
  default = true
}

data "aws_subnet" "default_public" {
  vpc_id            = data.aws_vpc.default.id
  availability_zone = var.default_public_subnet_az
  default_for_az    = true
}

# --- Modules ---

module "networking" {
  source = "./modules/networking"

  vpc_id                = data.aws_vpc.default.id
  availability_zone_a   = var.availability_zone_a
  availability_zone_b   = var.availability_zone_b
  private_subnet_a_cidr = var.private_subnet_a_cidr
  private_subnet_b_cidr = var.private_subnet_b_cidr
}

module "security" {
  source = "./modules/security"

  vpc_id           = data.aws_vpc.default.id
  app_port         = var.app_port
  app_ingress_cidr = var.app_ingress_cidr
}

module "database" {
  source = "./modules/database"

  db_name           = var.db_name
  db_username       = var.db_username
  db_password       = random_password.db_password.result
  kms_key_arn       = aws_kms_key.rds.arn
  subnet_ids        = module.networking.private_subnet_ids
  security_group_id = module.security.rds_security_group_id
}

module "compute" {
  source = "./modules/compute"

  subnet_id           = data.aws_subnet.default_public.id
  security_group_id   = module.security.app_security_group_id
  instance_type       = var.instance_type
  app_port            = var.app_port
  app_repository_url  = var.app_repository_url
  root_volume_size_gb = var.root_volume_size_gb
  availability_zone   = var.default_public_subnet_az
}
