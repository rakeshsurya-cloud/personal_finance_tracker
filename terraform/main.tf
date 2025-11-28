terraform {
  # --- Terraform Cloud Configuration ---
  # Uncomment and update this block to use Terraform Cloud
  # cloud {
  #   organization = "YOUR_ORG_NAME"
  #   workspaces {
  #     name = "finance-tracker-prod"
  #   }
  # }

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
  region = "us-west-2"
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

# Get the default VPC
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
  availability_zone = "us-west-2a"
  default_for_az    = true
}

resource "aws_security_group" "finance_app_sg" {
  name        = "finance_app_sg"
  description = "Allow SSH and Streamlit traffic"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Streamlit"
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
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

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ssm_policy" {
  role       = aws_iam_role.ssm_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_instance_profile" "ssm_profile" {
  name = "finance-app-ssm-profile"
  role = aws_iam_role.ssm_role.name
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

  user_data = <<-EOF
              #!/bin/bash
              dnf update -y
              dnf install -y python3.11 python3.11-pip git amazon-ssm-agent

              systemctl enable amazon-ssm-agent
              systemctl start amazon-ssm-agent

              git clone https://github.com/rakeshsurya-cloud/personal_finance_tracker.git /home/ec2-user/app
              cd /home/ec2-user/app
              
              # Install dependencies with Python 3.11
              python3.11 -m pip install -r requirements.txt
              
              # Setup Systemd Service
              cp finance-app.service /etc/systemd/system/finance-app.service
              systemctl daemon-reload
              systemctl enable finance-app
              systemctl start finance-app
              EOF

  tags = {
    Name = "FinanceAppServer"
  }
}
