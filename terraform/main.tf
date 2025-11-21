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

resource "aws_security_group" "finance_app_sg" {
  name        = "finance_app_sg"
  description = "Allow SSH and Streamlit traffic"

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

resource "aws_instance" "app_server" {
  ami           = data.aws_ami.amazon_linux.id  # Automatically uses the right AMI for your region
  instance_type = "t2.micro"
  key_name      = "finance-app-key" # Make sure to create this key pair in AWS Console first!
  
  security_groups = [aws_security_group.finance_app_sg.name]

  user_data = <<-EOF
              #!/bin/bash
              sudo yum update -y
              sudo yum install -y python3 python3-pip git
              git clone https://github.com/rakeshsurya-cloud/personal_finance_tracker.git /home/ec2-user/app
              cd /home/ec2-user/app
              pip3 install -r requirements.txt
              nohup streamlit run app.py &
              EOF

  tags = {
    Name = "FinanceAppServer"
  }
}
