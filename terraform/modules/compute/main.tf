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

locals {
  user_data = <<-EOT
              #!/bin/bash
              dnf update -y
              dnf install -y python3.11 python3.11-pip git amazon-ssm-agent

              systemctl enable amazon-ssm-agent
              systemctl start amazon-ssm-agent

              git clone ${var.app_repository_url} /home/ec2-user/app
              cd /home/ec2-user/app

              python3.11 -m pip install -r requirements.txt

              cp finance-app.service /etc/systemd/system/finance-app.service
              systemctl daemon-reload
              systemctl enable finance-app
              systemctl start finance-app
              EOT
}

resource "aws_instance" "app_server" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = var.instance_type

  iam_instance_profile        = aws_iam_instance_profile.ssm_profile.name
  subnet_id                   = var.subnet_id
  vpc_security_group_ids      = [var.security_group_id]
  associate_public_ip_address = true
  availability_zone           = var.availability_zone

  root_block_device {
    volume_size = var.root_volume_size_gb
    volume_type = "gp3"
  }

  user_data = local.user_data

  tags = {
    Name = "FinanceAppServer"
  }
}

output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.app_server.id
}

output "public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.app_server.public_ip
}

output "app_url" {
  description = "URL to access the application"
  value       = "http://${aws_instance.app_server.public_ip}:${var.app_port}"
}
