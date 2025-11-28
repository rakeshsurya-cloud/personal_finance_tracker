resource "aws_db_subnet_group" "finance_rds" {
  name       = "finance-rds-private"
  subnet_ids = var.subnet_ids

  tags = {
    Name = "finance-rds-private"
  }
}

data "aws_kms_alias" "rds" {
  name = "alias/aws/rds"
}

resource "aws_db_instance" "finance" {
  identifier           = "finance-app-db"
  db_name              = var.db_name
  engine               = "postgres"
  engine_version       = "15.4"
  instance_class       = "db.t3.micro"
  allocated_storage    = 20
  storage_type         = "gp2"
  storage_encrypted    = true
  kms_key_id           = coalesce(var.kms_key_arn, data.aws_kms_alias.rds.target_key_arn)
  username             = var.db_username
  password             = var.db_password
  db_subnet_group_name = aws_db_subnet_group.finance_rds.name

  vpc_security_group_ids  = [var.security_group_id]
  publicly_accessible     = false
  backup_retention_period = 7
  deletion_protection     = true
  multi_az                = false
  copy_tags_to_snapshot   = true
  skip_final_snapshot     = true

  tags = {
    Name = "FinanceAppPostgres"
  }
}

output "db_endpoint" {
  description = "RDS PostgreSQL endpoint"
  value       = aws_db_instance.finance.endpoint
}

output "db_master_username" {
  description = "Master username for the RDS instance"
  value       = aws_db_instance.finance.username
}
