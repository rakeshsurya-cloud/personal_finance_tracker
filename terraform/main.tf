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

# Automatically fetch the latest Amazon Linux 2023 AMI for the current region
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# Use the default VPC for cost-free networking primitives
data "aws_vpc" "default" {
  default = true
}

resource "aws_subnet" "private_a" {
  vpc_id                  = data.aws_vpc.default.id
  cidr_block              = "172.31.96.0/20"
  availability_zone       = "us-west-2a"
  map_public_ip_on_launch = false

  tags = {
    Name = "finance-private-a"
  }
}

resource "aws_subnet" "private_b" {
  vpc_id                  = data.aws_vpc.default.id
  cidr_block              = "172.31.112.0/20"
  availability_zone       = "us-west-2b"
  map_public_ip_on_launch = false

  tags = {
    Name = "finance-private-b"
  }
}

resource "aws_route_table" "private" {
  vpc_id = data.aws_vpc.default.id
}

resource "aws_route_table_association" "private_a" {
  subnet_id      = aws_subnet.private_a.id
  route_table_id = aws_route_table.private.id
}

resource "aws_route_table_association" "private_b" {
  subnet_id      = aws_subnet.private_b.id
  route_table_id = aws_route_table.private.id
}

# Get a public subnet in the default VPC
data "aws_subnet" "default" {
  vpc_id            = data.aws_vpc.default.id
  availability_zone = var.default_public_subnet_az
  default_for_az    = true
}

module "networking" {
  source = "./modules/networking"

  vpc_id                = data.aws_vpc.default.id
  availability_zone_a   = var.availability_zone_a
  availability_zone_b   = var.availability_zone_b
  private_subnet_a_cidr = var.private_subnet_a_cidr
  private_subnet_b_cidr = var.private_subnet_b_cidr
}

resource "aws_security_group" "rds" {
  name        = "finance_rds_sg"
  description = "Allow PostgreSQL access from the app security group"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description              = "PostgreSQL from app"
    from_port                = 5432
    to_port                  = 5432
    protocol                 = "tcp"
    security_groups          = [aws_security_group.finance_app_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# IAM Role for SSM access (so you can connect without SSH)
resource "aws_iam_role" "ssm_role" {
  name = "finance-app-ssm-role"

  vpc_id           = data.aws_vpc.default.id
  app_port         = var.app_port
  app_ingress_cidr = var.app_ingress_cidr
}

module "database" {
  source = "./modules/database"

  db_name           = var.db_name
  db_username       = var.db_username
  db_password       = random_password.db_password.result
  subnet_ids        = module.networking.private_subnet_ids
  security_group_id = module.security.rds_security_group_id
}

resource "aws_db_subnet_group" "finance_rds" {
  name       = "finance-rds-private"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]

  tags = {
    Name = "finance-rds-private"
  }
}

resource "aws_db_instance" "finance" {
  identifier              = "finance-app-db"
  db_name                 = "financeapp"
  engine                  = "postgres"
  engine_version          = "15.4"
  instance_class          = "db.t3.micro"
  allocated_storage       = 20
  max_allocated_storage   = 100
  storage_type            = "gp3"
  storage_encrypted       = true
  kms_key_id              = aws_kms_key.rds.arn
  username                = "finance_admin"
  password                = random_password.db_password.result
  db_subnet_group_name    = aws_db_subnet_group.finance_rds.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  publicly_accessible     = false
  backup_retention_period = 7
  deletion_protection     = true
  multi_az                = false
  performance_insights_enabled = true
  performance_insights_kms_key_id = aws_kms_key.rds.arn
  copy_tags_to_snapshot   = true
  skip_final_snapshot     = true

  tags = {
    Name = "FinanceAppPostgres"
  }
}

resource "aws_instance" "app_server" {
  ami           = data.aws_ami.amazon_linux.id # Automatically uses the right AMI for your region
  instance_type = "t3.micro"                   # Free-tier eligible in us-west-2
  key_name      = "finance-app-key"            # Make sure to create this key pair in AWS Console first!

  iam_instance_profile        = aws_iam_instance_profile.ssm_profile.name
  subnet_id                   = data.aws_subnet.default.id
  vpc_security_group_ids      = [aws_security_group.finance_app_sg.id]
  associate_public_ip_address = true

  root_block_device {
    volume_size = 30 # Increase to 30GB (minimum for this AMI, still free tier limit)
    volume_type = "gp3"
  }

  subnet_id             = data.aws_subnet.default_public.id
  security_group_id     = module.security.app_security_group_id
  instance_type         = var.instance_type
  app_port              = var.app_port
  app_repository_url    = var.app_repository_url
  root_volume_size_gb   = var.root_volume_size_gb
  availability_zone     = var.default_public_subnet_az
}
