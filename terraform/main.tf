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
  }
  required_version = ">= 1.2.0"
}

provider "aws" {
  region = "us-west-2"
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

resource "aws_instance" "app_server" {
  ami           = data.aws_ami.amazon_linux.id  # Automatically uses the right AMI for your region
  instance_type = "t3.micro"  # Free-tier eligible in us-west-2
  key_name      = "finance-app-key" # Make sure to create this key pair in AWS Console first!
  
  iam_instance_profile   = aws_iam_instance_profile.ssm_profile.name
  subnet_id              = data.aws_subnet.default.id
  vpc_security_group_ids = [aws_security_group.finance_app_sg.id]
  associate_public_ip_address = true

  root_block_device {
    volume_size = 20  # Increase from default 8GB to 20GB (still free tier)
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
