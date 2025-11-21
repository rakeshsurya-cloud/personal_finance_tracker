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
  region = "us-east-1"
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
  ami           = "ami-053b0d53c279acc90" # Ubuntu 22.04 LTS (us-east-1)
  instance_type = "t2.micro"
  key_name      = "finance-app-key" # Make sure to create this key pair in AWS Console first!
  
  security_groups = [aws_security_group.finance_app_sg.name]

  user_data = <<-EOF
              #!/bin/bash
              sudo apt-get update
              sudo apt-get install -y python3-pip git
              git clone https://github.com/rakeshsurya-cloud/personal_finance_tracker.git /home/ubuntu/app
              cd /home/ubuntu/app
              pip3 install -r requirements.txt
              nohup streamlit run app.py &
              EOF

  tags = {
    Name = "FinanceAppServer"
  }
}
