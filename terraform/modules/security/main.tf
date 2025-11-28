resource "aws_security_group" "app" {
  name        = "finance_app_sg"
  description = "Allow application traffic"
  vpc_id      = var.vpc_id

  ingress {
    description = "Application port"
    from_port   = var.app_port
    to_port     = var.app_port
    protocol    = "tcp"
    cidr_blocks = [var.app_ingress_cidr]
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
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from app"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

output "app_security_group_id" {
  description = "Security group ID for the app server"
  value       = aws_security_group.app.id
}

output "rds_security_group_id" {
  description = "Security group ID for the RDS instance"
  value       = aws_security_group.rds.id
}
